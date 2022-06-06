import pexpect
import logging
import shutil
import socket
import json
import time

from arch import Arch, ARCH_CMDS

USER_PROMPT = "$ "
ROOT_PROMPT = "# "

# QMP commands supported by iot-suite
SUPPORTED_CMDS = ["quit", "loadvm", "savevm", "qmp_capabilities"]
# path of the QMP socket
QMP_PATH = "localhost"

logger = logging.getLogger()

class QMPCommand:
    """
    Represents a command to be sent to QEMU via QMP.
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
    def __init__(self, arch: Arch, user, passwd, image, qmp_port):
        self.arch = arch
        self.user = user
        self.passwd = passwd
        self.image = image
        self.qmp_port = qmp_port

class CmdResult:
    """
    Result of a command run on the sandbox VM
    """
    def __init__(self, exitcode, output):
        self.exitcode = exitcode
        self.output = output

class Qemu:
    
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

    def noninteractive(self):
        """
        Starts an automated QEMU session. This is primarily used by the
        sandbox to automate data gathering.
        """
        self._startup()

    def login(self):
        """
        Login to the QEMU VM instance. This is usually done automatically
        and should not be called by the end user.
        """
        if not self._check_started():
            # todo: raise error
            logger.error("error: qemu instance not started")
            return

        try:
            self.proc.expect("iotsuite login: ")
        except:
            logger.error(f"error: could not login: got '{self.proc.before}'")
            self.stop()
            return
        
        logger.debug("sending user")
        self.proc.sendline(f"{self.config.user}")
        if self.proc.expect("Password: ") != 0:
            # todo: raise error, stop instance from calling function
            logger.error("error: did not receive password prompt")
            self.stop()
            return

        logger.debug("sending password")
        self.proc.sendline(f"{self.config.passwd}")
        if self.proc.expect(f"{self.prompt}") != 0:
            # todo: raise login error
            logger.error("error: could not log in")

    def run_cmd(self, cmd):
        """
        Run a command on the sandbox VM. This is used by a non-interactive session.
        """
        if not self._check_started():
            logger.error("error: could not run cmd: VM not started")
        
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

        return CmdResult(exitcode, output.decode("ascii").strip())
        

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
        e = self.send_qmp_cmd(QMPCommand("quit"))

        if not check_res_err(e):
            # todo: raise error
            logger.error(f"error: did not quit, received QEMU response {e}")
            return

        self.proc.expect(pexpect.EOF)


    def reset(self):
        """
        Reset the VM to a clean instance.
        """
        pass

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

    def _check_started(self):
        return self.started and hasattr(self, "proc")

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

        # receive, process and decode reply
        reply = self.qmp.recv(1024).decode("ascii").rstrip().split('\r\n')

        # there may be multiple items in the reply, so decode all and return
        # the first one (which is usually the most relevant)
        return [json.loads(r) for r in reply][0]
    
    def _startup(self):
        # set up the additional arguments needed to run the sandbox
        self._construct_cmd()

        # start the sandbox
        self.proc = pexpect.spawn(self._cmd, self._cmd_args, timeout=60)
        self.started = True

        # sleep for a second to give the VM time to start up the QMP server
        time.sleep(1)
        self._init_qmp()

        # attempt login
        logger.debug("attempting login")
        self.login()

    def _construct_cmd(self):
        self._cmd_args.extend(self._ADDITIONAL_ARGS)

        logger.debug(f"running command: '{self._cmd} {self._cmd_args}'")

if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    logger.addHandler(handler)

    config = QemuConfig(Arch.ARM, "root", "toor", "../vms/arm", 4444)
    q = Qemu(config)
    q.noninteractive()

    logger.debug("running test command")
    result = q.run_cmd("ls")
    print(f'"{result.output}"', result.exitcode)

    q.stop()