import pexpect
import subprocess
import logging
import shutil
import socket
import json
import time

from fabric import Connection
from invoke.exceptions import UnexpectedExit, CommandTimedOut

from .config import Config, QemuConfig
from .arch import Arch, ARCH_CMDS
from .utils import IoTSuiteError
import iotsuite.utils as utils

USER_PROMPT = "$ "
ROOT_PROMPT = "# "

# QMP commands supported by iot-suite
SUPPORTED_CMDS = ["quit", "loadvm", "savevm", "qmp_capabilities"]
# path of the QMP socket
QMP_PATH = "localhost"
QEMU_MONITOR_PROMPT = "(qemu)"

logger = utils.logger.getChild("qemu")

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

class QemuError(IoTSuiteError):
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
        self.ssh = None
        self.proc = None
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
    def image(self):
        return self.config.image

    @property
    def macaddr(self):
        return self.config.macaddr

    @property
    def helper(self):
        return self.config.nic_helper

    @property
    def started(self):
        try:
            return self._check_started()
        except AttributeError:
            return False

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
            if self._ssh_is_active():
                self.awaiting = self.conn.run(cmd, hide=True, asynchronous=True)
                if not wait:
                    return None
            else:
                raise QemuError("ssh is not initiated")
        
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
            logger.debug(f"output: {output.decode('ascii')}")
        
            # run check for exit code
            self.proc.sendline("echo $?")
            #? same for this one
            if self.proc.expect(self.prompt) != 0:
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
            except CommandTimedOut as e:
                result = e.result
            except UnexpectedExit as e:
                result = e.result
            output = result.stdout if result.exited == 0 else result.stderr

            self.awaiting = None
            return CmdResult(result.exited, output.strip())

    def terminate_existing(self, prog=None):
        """
        Terminate an existing running command.

        Due to the API of the backing SSH library, `prog` is required if the backing
        connection is SSH-based, as it runs `pkill` to kill the command.
        A `QemuError` is raised if `prog` is not provided.
        """
        if self.awaiting is None:
            raise QemuError("no currently running command")
        if not self.ssh:
            self.proc.sendcontrol('c')
        else:
            if prog is None:
                raise QemuError("cannot terminate command on SSH without given prog")
            else: #! this is janky as fuck - please please PLEASE find a better solution
                try:
                    self.conn.run(f"sudo pkill -SIGINT {prog}")
                except UnexpectedExit:
                    raise QemuError(f"failed to properly terminate program '{prog}'")
        return self.wait_existing()
        
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

    def stop(self, force=False):
        """
        Stops the VM via the QEMU monitor or QMP.
        """
        logger.debug("stopping QEMU VM")

        if not self._check_started():
            # if not started, don't do anything
            logger.debug("QEMU process not started, returning")
            return

        if self.awaiting is not None and not force:
            raise QemuError("attempted to stop QEMU controller while still awaiting")

        if self._ssh_is_active():
            self.conn.close()
            delattr(self, "conn")

        if self.config.qmp:
            e = self.send_qmp_cmd(QMPCommand("quit"))

            if not check_res_err(e):
                raise QemuError(f"did not quit, received QEMU response {e}")
            
            self.qmp.shutdown(socket.SHUT_RDWR)
            self.qmp.close()

        else:
            self._enter_qemu_monitor()
            self.proc.sendline("quit")

        self.proc.expect(pexpect.EOF)

        if not self.proc.isalive():
            self.proc.wait()

        self.proc = None

    def reset(self, tag):
        """
        Reset the VM to a clean instance.

        Raises `QemuError` if architecture is MIPS or MIPSEL, due to a bug
        in the implementation of `qemu-system-mips{,el}` requiring the reset
        to be performed offline using `qemu-img`, invoked via `offline_reset()`.
        """

        logger.debug(f"resetting qemu to state {tag}")

        if not self.started:
            raise QemuError("cannot perform live reset when VM is not running")

        if self.config.qmp:
            logger.error("cannot perform system reset via QMP")
            self.send_qmp_cmd(QMPCommand("loadvm", tag=tag))
        elif not self.needs_offline_reset():
            self.send_qemu_command("loadvm", [tag])
        else:
            raise QemuError(f"architecture {self.arch} needs offline reset")

    def snapshot(self, tag):
        """
        Create a clean snapshot of a VM.

        Raises `QemuError` if architecture is MIPS or MIPSEL, due to a bug
        in the implementation of `qemu-system-mips{,el}` requiring the reset
        to be performed offline using `qemu-img`, invoked via `offline_reset()`.
        """

        if not self.started:
            raise QemuError("cannot perform live snapshot when VM is not running")

        logger.debug(f"taking snapshot with tag {tag}")

        if self.config.qmp:
            self.send_qmp_cmd(QMPCommand("savevm", tag=tag))
        elif not self.needs_offline_reset():
            self.send_qemu_command("savevm", [tag])
        else:
            raise QemuError(f"architecture {self.arch} needs offline snapshot")

    def offline_reset(self, tag):
        """
        Reset to VM to a clean instance while not running.

        This has to be done for MIPS and MIPSEL sandboxes as there
        is a bug in QEMU resulting in a segfault when `loadvm` is run
        on a live instance.
        """
        if self.started:
            raise QemuError("cannot perform offline reset while QEMU is running")

        logger.debug(f"running offline reset on {self.image} to tag {tag}")
        
        self._run_qemu_img("-a", tag)
        

    def offline_snapshot(self, tag):
        """
        Create a clean snapshop of a VM while not running.

        This has to be done for MIPS and MIPSEL sandboxes as there
        is a bug in QEMU result in a segfault when `savevm` is run
        on a live instance.
        """

        if self.started:
            raise QemuError("cannot perform offline snapshot while QEMU is running")

        logger.debug(f"taking offline screenshot on {self.image} with tag {tag}")

        self._run_qemu_img("-c", tag)
    
    def needs_offline_reset(self):
        """
        Returns `True` if the QEMU instance needs to be reset offline.
        """
        return (
            self.arch == Arch.MIPS or self.arch == Arch.MIPSEL
        )

    #! ================== PRIVATE METHODS ===================

    def _check_started(self):
        return isinstance(self.proc, pexpect.spawn) and self.proc.isalive()

    def _expect_login_prompt(self, prompt):
        try:
            logger.debug("waiting for login prompt")
            self.proc.expect_exact(f"{prompt}")
            logger.debug(f"output before: {self.proc.before}")
        except pexpect.EOF:
            raise QemuError(f"unexpected EOF when waiting for login")
        except pexpect.TIMEOUT:
            raise QemuError(f"expect timed out while waiting for login prompt")
        except KeyboardInterrupt as e:
            logger.debug("got ctrl-c, assuming VM did not start on time")
            logger.debug("dumping proc before:")
            logger.debug(f"{self.proc.before}")
            raise e

    def _init_ssh(self, remote_ip, port=22):
        if not self._check_started():
            raise QemuError("attempted to initialize ssh when not started")
        
        self._expect_login_prompt(self.config.login_prompt)

        self.conn = Connection(remote_ip, 
            user=self.config.user, port=port,
            connect_kwargs={
                "password" : self.config.passwd
            }
        )

    def _ssh_is_active(self):
        return hasattr(self, "conn")

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
            raise QemuError("did not receive qemu prompt")

    def _exit_qemu_monitor(self):
        self.proc.sendcontrol('a')
        # sendline to send a newline and elicit the prompt to reappear
        self.proc.sendline('c')

        if self.proc.expect(self.prompt) != 0:
            raise QemuError("did not receive qemu prompt")

    def _run_qemu_img(self, action, tag):
        # todo: BETTER ERROR HANDLING GOOD GOD
        subprocess.run(
            ["qemu-img", "snapshot", action, tag, f"{self.image}/rootfs.qcow2"]
        )
    
    def _startup(self):
        # set up the additional arguments needed to run the sandbox
        self._construct_cmd()

        # start the sandbox
        self.proc = pexpect.spawn(
            self._cmd, self._cmd_args,
            maxread=1,
            timeout=self.config.timeout
        )

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
        if i == 3:
            try:
                vm.stop()
            except QemuError as e:
                logger.error(f"{e}")
        time.sleep(1)

    result = vm.wait_existing()

    print(f'"{result.output}"', result.exitcode)

    logger.debug("running second test command")
    result2 = c2.run_cmd("ls")
    print(f'"{result2.output}"', result2.exitcode)

    #vm.send_qemu_command("savevm", ["loaded"])

    vm.stop()
    c2.stop()

    # logger.debug("restarting VM")
    # q.noninteractive()

    # logger.debug("running second test command")
    # result = q.run_cmd("pwd")
    # print(f'"{result.output}"', result.exitcode)

    # q.stop()