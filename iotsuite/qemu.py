import pexpect
import logging
import shutil
import socket
import json
import time
import sys

from fabric import Connection
from invoke.exceptions import UnexpectedExit

from config import Config, QemuConfig
from arch import Arch, ARCH_CMDS

USER_PROMPT = "$ "
ROOT_PROMPT = "# "

# QMP commands supported by iot-suite
SUPPORTED_CMDS = ["quit", "loadvm", "savevm", "qmp_capabilities"]
# path of the QMP socket
QMP_PATH = "localhost"
QEMU_MONITOR_PROMPT = "(qemu)"

logger = logging.getLogger("qemu")

class QMPCommand:
    """
    Represents a QMP command that can be sent to QEMU.
    """
    def __init__(self, cmd, **params):
        self.execute = cmd
        self.arguments = dict(params)

    @staticmethod
    def quit():
        return QMPCommand("quit")

    @staticmethod
    def loadvm(tag):
        return QMPCommand("loadvm", tag=tag)

    @staticmethod
    def savevm(tag):
        return QMPCommand("savevm", tag=tag)

    @staticmethod
    def qmp_capabilities():
        return QMPCommand("qmp_capabilities")
    
    def to_json(self):
        return json.dumps(self.__dict__, indent=4)

    def supported(self):
        return self.execute in SUPPORTED_CMDS

def check_res_err(res):
    return "return" in res and not res["return"]

class QemuError(Exception):
    """
    An exception raised when there is an error condition in the execution
    of the Qemu controller.

    Note that commands that exit with a non-zero error code do not raise this
    exception, they are returned as a `CmdResult` with an exitcode > 0. This
    exception pertains to error conditions in the running of the controller and
    the VM it controls.
    """
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return f"{self.msg}"

class CmdResult:
    """
    Result of a command run on the sandbox VM.

    This object should not be constructed directly, but instead
    returned as a result of waiting on commands.
    """
    def __init__(self, exitcode, output):
        self.exitcode = exitcode
        self.output = output

class Qemu:
    """
    The class controlling the behaviour of the QEMU emulator that
    runs the sandbox and C2 virtual machines.

    Each Qemu instance represents a QEMU VM that can either be
    active or inactive. It can be started interactively or non-interactively.

    Interactive mode allows the user to interact with the VM as if it were
    a command line program, while non-interactive mode allows the VM to be
    controlled programmatically. Commands can be sent via the `run_cmd` method
    and the exitcode as well as any program output will be piped back
    and returned as a `CmdResult`.

    Qemu objects in noninteractive mode can also have commands be run 
    asynchronously and waited for when the result is needed. This allows other 
    code to be run between executing the command and reaping the result, or custom
    input to be sent to the command if needed.
    """    
    def __init__(self, config: QemuConfig):
        if config.qmp:
            self._ADDITIONAL_ARGS = ["-nographic",
                "-serial", "stdio",
                "-qmp", f"tcp:{QMP_PATH}:{config.qmp_port},server,wait=off",
            ]
        else:
            self._ADDITIONAL_ARGS = [
                "-nographic", "-serial", "mon:stdio",
            ]
        
        self.config = config
        self.started = False
        self.is_interactive = True

        # the currently running job, if run asynchronously.
        # will be a `fabric.Promise` if running on SSH
        self.awaiting = None

        # construct the command to execute
        vmdir= self.config.image
        self._cmd = shutil.which(ARCH_CMDS[self.config.arch])
        if self._cmd is None:
            raise QemuError(f"no qemu system executable for arch '{self.config.arch}'")

        self._cmd_args = self.config.arch.args(vmdir, self.helper, self.macaddr)
        self.prompt = ROOT_PROMPT if self.config.user == "root" else USER_PROMPT

    @property
    def arch(self):
        return self.config.arch

    @property
    def macaddr(self):
        return self.config.macaddr

    @property
    def helper(self):
        return self.config.nic_helper

    def interactive(self, ssh=None):
        """
        Starts an interactive QEMU session. This can be interacted with
        by the user.
        """
        pass

    def noninteractive(self, ssh=None):
        """
        Starts an automated QEMU session. This is primarily used by the
        sandbox to automate data gathering.

        If the keyword argument `ssh` is present, it should be a tuple of
        (str, int) indicating the remote ip/domain and port number.
        """
        if self.started:
            raise QemuError("QEMU controller already running")
        
        self._startup()

        if ssh is None:
            self.ssh = False

            # attempt login
            logger.debug("attempting login")
            self.login(self.config.login_prompt)
        
        else:
            self.ssh = True
            self._init_ssh(ssh[0], port=ssh[1])

    def login(self, login_prompt):
        """
        Login to the QEMU VM instance via pexpect. This is usually done automatically
        and should not be called by the end user.
        """
        if not self._check_started():
            raise QemuError("QEMU instance not started")

        self._expect_login_prompt(login_prompt)
        
        logger.debug("sending user")
        self.proc.sendline(f"{self.config.user}")
        if self.proc.expect("Password: ") != 0:
            # todo: stop instance from calling function
            raise QemuError("did not receive password prompt")

        logger.debug("sending password")
        self.proc.sendline(f"{self.config.passwd}")
        try:
            self.proc.expect(f"{self.prompt}")
        except:
            # todo: stop instance from calling function
            raise QemuError(f"could not login: got '{self.proc.before}'")

    def run_cmd(self, cmd, wait=True):
        """
        Run a command on the sandbox VM. This is used by a non-interactive session.

        `wait` determines whether or not the Qemu controller waits for the command
        to complete. Setting it to `False` allows the user to expect custom output from
        the command or run additional operations before waiting it for completion. If
        `wait` is set to `True`, the command is waited for immediately after invocation
        and a `CmdResult` is directly returned. Else, `None` is returned, and the command
        has to be reaped via `wait_existing()`.

        Important to note is that `wait` does not allow `Qemu` to run multiple commands
        simultaneously. Due to the synchronous nature of the data collection procedure,
        this functionality, while supported by the backend, is not implemented in `Qemu`.
        `wait` only exists to allow the user to run additional code locally or perform
        additional work on a currently running command.
        """
        if not self._check_started():
            raise QemuError("could not run cmd: VM not started")

        if not self.ssh:
        
            self.proc.sendline(cmd)
            self.awaiting = cmd
            if not wait:
                return None
            
        else:
            self.awaiting = self.conn.run(cmd, hide=True, asynchronous=True)
            if not wait:
                return None
        
        return self.wait_existing()

    def expect(self, pattern):
        """
        Expect a particular pattern of output from the command.
        """
        #todo
        pass

    def wait_existing(self):
        """
        Wait on a currently running command.
        """
        if self.awaiting is None:
            raise QemuError("no currently running command")
        
        if not self.ssh:
            # expect command prompt to confirm command completion
            #? confirm that this check is the proper way to do this
            if self.proc.expect(f"{self.prompt}") != 0:
                # todo: provide additional info
                raise QemuError("error while expecting command prompt")

            # save output to a local string
            output = self.proc.before
        
            # run check for exit code
            self.proc.sendline("echo $?")
            #? same for this one
            if self.proc.expect(self.prompt) != 0:
                # todo: raise error
                raise QemuError("error while expecting command prompt")

            # parse exit code from output
            exitcode = int(
                self.proc.before.split(b'\r\r\n')[1].decode("ascii")
            )

            # assume self.awaiting was set to the command, since not ssh
            output = output.decode("ascii").strip().lstrip(f"{self.awaiting}\r\r\n")

            # unset awaiting
            self.awaiting = None

            return CmdResult(exitcode, output)

        else:
            try:
                # try to join on promise
                result = self.awaiting.join()
            except UnexpectedExit as e:
                result = e.result
            output = result.stdout if result.exited == 0 else result.stderr

            self.awaiting = None
            return CmdResult(result.exited, output.strip())
        
    def send_qmp_cmd(self, cmd):
        """
        Send a QMP command through a network socket. This cannot be run
        if the QEMU controller is configured to send monitor commands
        through the QEMU monitor.

        Raises `QemuError` if the controller is not configured for QMP or
        the command being sent is not supported by IoTSuite.
        """

        if not cmd.supported():
            raise QemuError(f"QMP command {cmd.execute} is not supported")

        if not self.config.qmp:
            raise QemuError("QEMU controller is not configured for QMP")
        
        logger.debug(f"sending QMP command {cmd.execute}")
        return self._send_qmp(cmd.to_json())

    def send_qemu_command(self, cmd, args):
        """
        Send a QEMU monitor command through the standard streams. This cannot
        be run if the QEMU controller is configured to send QMP commands.

        Raises `QemuError` if the controller is configured for QMP.
        """

        if self.config.qmp:
            raise QemuError("QEMU controller is configured for QMP")

        logger.debug(f"sending QEMU monitor command {cmd} with args {args}")
        
        to_send = f"{cmd} {' '.join(args)}"
        self._enter_qemu_monitor()
        self.proc.sendline(to_send)
        self.proc.expect(QEMU_MONITOR_PROMPT)
        self._exit_qemu_monitor()

    def stop(self):
        """
        Stops the VM via the QEMU monitor or QMP.
        """
        logger.debug("stopping QEMU VM")


        if not self._check_started():
            # if not started, don't do anything
            logger.debug("QEMU process not started, returning")
            return

        if self.awaiting is not None:
            raise QemuError("QEMU is still awaiting command")

        if self.ssh:
            self.conn.close()

        if self.config.qmp:
            e = self.send_qmp_cmd(QMPCommand("quit"))

            if not check_res_err(e):
                # todo: raise error
                logger.error(f"error: did not quit, received QEMU response {e}")
                return
            
            self.qmp.shutdown(socket.SHUT_RDWR)
            self.qmp.close()

            self.proc.expect(pexpect.EOF)
            self.started = False

        else:
            self._enter_qemu_monitor()
            self.proc.sendline("quit")

        delattr(self, "proc")

    def reset(self, tag):
        """
        Reset the VM to a clean instance.

        Raises `QemuError` if architecture is MIPS or MIPSEL, due to a bug
        in the implementation of `qemu-system-mips{,el}` requiring the reset
        to be performed offline using `qemu-img`, invoked via `offline_reset()`.
        """

        #todo: add check for architecture
        if self.config.qmp:
            logger.error("error: cannot perform system reset via QMP")
            self.send_qmp_cmd(QMPCommand("loadvm", tag=tag))
        else:
            self.send_qemu_command("loadvm", [tag])

    def snapshot(self, tag):
        """
        Create a clean snapshot of a VM.
        """
        self.send_qmp_cmd(QMPCommand("savevm", tag=tag))

    def offline_reset(self):
        """
        Reset to VM to a clean instance while not running.

        This has to be done for MIPS and MIPSEL sandboxes as there
        is a bug in QEMU resulting in a segfault when `savevm` is run
        on a live instance.
        """
        if self.started:
            raise QemuError("cannot perform offline reset while QEMU is running")
        
        #todo
        pass

    #! ================== PRIVATE METHODS ===================

    def _check_started(self):
        return self.started and hasattr(self, "proc")

    def _expect_login_prompt(self, prompt):
        try:
            self.proc.expect(f"{prompt}")
        except:
            # todo: raise error
            logger.error(f"error: could not login: got '{self.proc.before}'")
            self.stop()
            sys.exit(1)

    def _init_ssh(self, remote_ip, port=22):
        if not self._check_started():
            # todo: raise error
            return
        
        self._expect_login_prompt(self.config.login_prompt)

        self.conn = Connection(remote_ip, 
            user=self.config.user, port=port,
            connect_kwargs={
                "password" : self.config.passwd
            }
        )

    def _init_qmp(self):
        # hook up to the QMP socket
        self.qmp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.qmp.connect(("localhost", self.config.qmp_port))

        # receive and process the greeting message
        res = self.qmp.recv(1024).decode("ascii")
        self.qmp_startup = json.loads(res)

        # send qmp_capabilities command to exit negotiation
        self._send_qmp(QMPCommand("qmp_capabilities").to_json())
        
    def _send_qmp(self, cmd):
        # send a command string on the qmp socket
        self.qmp.send(bytes(cmd.encode("ascii")))

        for _ in range(5): # receive, process and decode reply
            reply = self.qmp.recv(1024).decode("ascii").rstrip().split('\r\n')
            replies = [json.loads(r) for r in reply]

            for r in replies:
                if "return" in r:
                    return r

        # there may be multiple items in the reply, so decode all and return
        # the first one (which is usually the most relevant)
        return replies[0]

    def _enter_qemu_monitor(self):
        self.proc.sendcontrol('a')
        self.proc.send('c')

        if self.proc.expect(QEMU_MONITOR_PROMPT) != 0:
            # todo: raise error
            logger.error("error: did not receive qemu prompt")
            return

    def _exit_qemu_monitor(self):
        self.proc.sendcontrol('a')
        self.proc.sendline('c')

        if self.proc.expect(self.prompt) != 0:
            # todo: raise error
            logger.error("error: did not receive qemu prompt")
            return
    
    def _startup(self):
        # set up the additional arguments needed to run the sandbox
        self._construct_cmd()

        # start the sandbox
        self.proc = pexpect.spawn(self._cmd, self._cmd_args, timeout=60)
        self.started = True

        # sleep for a second to give the VM time to start up the QMP server
        time.sleep(1)
        
        if self.config.qmp:
            self._init_qmp()

    def _construct_cmd(self):
        self._cmd_args.extend(self._ADDITIONAL_ARGS)

        logger.debug(f"running command: '{self._cmd} {self._cmd_args}'")

if __name__ == "__main__":
    import time

    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    logger.addHandler(handler)

    config = Config("../configs/iotsuite.conf")

    vm_config = QemuConfig(
        Arch.ARM, 
        config.ARM["Username"],
        config.ARM["Password"],
        config.ARM["Image"],
        config.NETWORK["NicHelper"],
        config.ARM["MacAddr"],
        "iotsuite login: "
    )

    c2_config = QemuConfig(
        Arch.CNC,
        config.CNC["Username"],
        config.CNC["Password"],
        "../vms/cnc", 
        config.NETWORK["NicHelper"],
        config.CNC["MacAddr"],
        "iotsuite-c2 login: ", 
        qmp_port=int(config.CNC["QMPPort"]), qmp=config.CNC.qmp()
    )

    vm = Qemu(vm_config)
    c2 = Qemu(c2_config)

    logger.debug("starting up vm")
    vm.noninteractive()

    logger.debug("starting up fake c2")
    c2.noninteractive(ssh=("192.168.0.2", 2222))

    logger.debug("running test command")
    vm.run_cmd("ls", wait = False)

    print("")
    for i in range(5):
        print(f"waiting - seconds elapsed: {i}\r", end="")
        time.sleep(1)

    result = vm.wait_existing()

    print(f'"{result.output}"', result.exitcode)

    logger.debug("running second test command")
    result2 = c2.run_cmd("ls")
    print(f'"{result2.output}"', result2.exitcode)

    vm.send_qemu_command("savevm", ["loaded"])

    vm.stop()
    c2.stop()

    # logger.debug("restarting VM")
    # q.noninteractive()

    # logger.debug("running second test command")
    # result = q.run_cmd("pwd")
    # print(f'"{result.output}"', result.exitcode)

    # q.stop()