import pexpect
import logging
import shutil
import socket
import json
import time
import sys

from fabric import Connection

from arch import Arch, ARCH_CMDS

USER_PROMPT = "$ "
ROOT_PROMPT = "# "

# QMP commands supported by iot-suite
SUPPORTED_CMDS = ["quit", "loadvm", "savevm", "qmp_capabilities"]
# path of the QMP socket
QMP_PATH = "localhost"

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

class QemuConfig:
    """
    Configuration of a QEMU instance
    """
    def __init__(self, arch: Arch, user, passwd, image, qmp_port, login_prompt):
        self.arch = arch
        self.user = user
        self.passwd = passwd
        self.image = image
        self.qmp_port = qmp_port
        self.login_prompt = login_prompt

class CmdResult:
    """
    Result of a command run on the sandbox VM
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
    """    
    def __init__(self, config: QemuConfig):
        self._ADDITIONAL_ARGS = ["-nographic",
            "-serial", "stdio",
            "-qmp", f"tcp:{QMP_PATH}:{config.qmp_port},server,wait=off",
        ]

        self.config = config
        self.started = False
        self.is_interactive = True

        # construct the command to execute
        vmdir= self.config.image
        self._cmd = shutil.which(ARCH_CMDS[self.config.arch])
        if self._cmd is None:
            # todo: return error
            logger.error("error: no command given")
            pass

        self._cmd_args = self.config.arch.args(vmdir)
        self.prompt = ROOT_PROMPT if self.config.user == "root" else USER_PROMPT

    def interactive(self):
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
            # todo: raise error
            return
        
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
            # todo: raise error
            logger.error("error: qemu instance not started")
            return

        self._expect_login_prompt(login_prompt)
        
        logger.debug("sending user")
        self.proc.sendline(f"{self.config.user}")
        if self.proc.expect("Password: ") != 0:
            # todo: raise error, stop instance from calling function
            logger.error("error: did not receive password prompt")
            self.stop()
            return

        logger.debug("sending password")
        self.proc.sendline(f"{self.config.passwd}")
        try:
            self.proc.expect(f"{self.prompt}")
        except:
            # todo: raise error instead of exiting
            logger.error(f"error: could not login: got '{self.proc.before}'")
            self.stop()
            sys.exit(1)

    def run_cmd(self, cmd):
        """
        Run a command on the sandbox VM. This is used by a non-interactive session.
        """
        if not self._check_started():
            # todo: raise error
            logger.error("error: could not run cmd: VM not started")
            sys.exit(1)

        if not self.ssh:
        
            self.proc.sendline(cmd)
            
            if self.proc.expect(f"{self.prompt}") != 0:
                # todo: raise error
                return CmdResult(1, "")

            output = self.proc.before
            
            self.proc.sendline("echo $?")
            if self.proc.expect(self.prompt) != 0:
                # todo: raise error
                return CmdResult(1, "")

            exitcode = int(
                self.proc.before.split(b'\r\r\n')[1].decode("ascii")
            )

            output = output.decode("ascii").strip().lstrip(f"{cmd}\r\r\n")

            return CmdResult(exitcode, output)
        else:
            result = self.conn.run(cmd, hide=True)
            output = result.stdout if result.exited == 0 else result.stderr
            return CmdResult(result.exited, output)
        
    def send_qmp_cmd(self, cmd):
        if not cmd.supported():
            # todo: raise error
            return
        
        return self._send_qmp(cmd.to_json())

    def stop(self):
        """
        Stops the VM via the QEMU monitor.
        """
        logger.debug("stopping QEMU VM")

        if self.ssh:
            self.conn.close()
        
        e = self.send_qmp_cmd(QMPCommand("quit"))

        if not check_res_err(e):
            # todo: raise error
            logger.error(f"error: did not quit, received QEMU response {e}")
            return
        
        self.qmp.shutdown(socket.SHUT_RDWR)
        self.qmp.close()

        self.proc.expect(pexpect.EOF)
        self.started = False

    def reset(self, tag):
        """
        Reset the VM to a clean instance.
        """
        self.send_qmp_cmd(QMPCommand("loadvm", tag=tag))

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
            # todo: raise error
            return
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
    
    def _startup(self):
        # set up the additional arguments needed to run the sandbox
        self._construct_cmd()

        # start the sandbox
        self.proc = pexpect.spawn(self._cmd, self._cmd_args, timeout=60)
        self.started = True

        # sleep for a second to give the VM time to start up the QMP server
        time.sleep(1)
        self._init_qmp()

    def _construct_cmd(self):
        self._cmd_args.extend(self._ADDITIONAL_ARGS)

        logger.debug(f"running command: '{self._cmd} {self._cmd_args}'")

if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    logger.addHandler(handler)

    # suppress paramiko logging
    #logging.getLogger("paramiko").setLevel(logging.WARNING)
    #logging.getLogger("invoke").setLevel(logging.WARNING)

    vm_config = QemuConfig(
        Arch.ARM, 
        "root", "toor", 
        "../vms/arm", 4444, 
        "iotsuite login: "
    )

    c2_config = QemuConfig(
        Arch.CNC,
        "tester", "itestmalware",
        "../vms/cnc", 4445,
        "iotsuite-c2 login: "
    )

    vm = Qemu(vm_config)
    c2 = Qemu(c2_config)

    logger.debug("starting up vm")
    vm.noninteractive()

    logger.debug("starting up fake c2")
    c2.noninteractive(ssh=("192.168.0.2", 2222))

    logger.debug("running test command")
    result = vm.run_cmd("ls")
    print(f'"{result.output}"', result.exitcode)

    logger.debug("running second test command")
    result2 = c2.run_cmd("ls")
    print(f'"{result2.output}"', result2.exitcode)

    vm.stop()
    c2.stop()

    # logger.debug("restarting VM")
    # q.noninteractive()

    # logger.debug("running second test command")
    # result = q.run_cmd("pwd")
    # print(f'"{result.output}"', result.exitcode)

    # q.stop()