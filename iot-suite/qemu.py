import pexpect
import logging
import shutil
import os

from .arch import Arch, ARCH_CMDS

USER_PROMPT = "$"
ROOT_PROMPT = "#"

# QMP commands supported by iot-suite
SUPPORTED_CMDS = ["quit", "loadvm", "savevm"]
# path of the QMP pipe
QMP_FIFO_PATH = "/tmp/sandbox"

logger = logging.getLogger()

class QemuConfig:
    """
    Configuration of a QEMU instance
    """
    def __init__(self, arch: Arch, user, passwd, image):
        self.arch = arch
        self.user = user
        self.passwd = passwd
        self.image = image

class CmdResult:
    """
    Result of a command run on the sandbox VM
    """
    def __init__(self, exitcode, output):
        self.exitcode = exitcode
        self.output = output

class Qemu:
    _ADDITIONAL_ARGS = ["-nographic",
        "-serial", "mon:stdio",
        "-chardev", f"pipe,id=mon0,path={QMP_FIFO_PATH}",
        "-mon", "chardev=mon0,mode=control",
    ]
    
    def __init__(self, config):
        self.config = config
        self.started = False
        self.is_interactive = True

        # construct the command to execute
        vmdir, kern = self.config.image, f"{self.config.image}/kernel.img"
        self._cmd = shutil.which(ARCH_CMDS[self.config.arch])
        if self._cmd is None:
            # todo: return error
            pass

        self._cmd_args = self.config.arch.args(vmdir, kern)
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

        self.proc.expect("iotsuite login: ")
        logger.debug("Sending user")
        self.proc.sendline(f"{self.config.user}")
        if self.proc.expect("Password: ") != 0:
            # todo: raise error, stop instance from calling function
            logger.error("error: did not receive password prompt")
            self.stop()
            return

        logger.debug("Sending password")
        self.proc.sendline(f"{self.config.passwd}")
        if self.proc.expect(f"{self.prompt}") != 0:
            # todo: raise login error
            logger.error("error: could not log in")

    def run_cmd(self, cmd):
        """
        Run a command on the sandbox VM. This is used by a non-interactive session.
        """
        if not self._check_started():
            logger.error("error: could not run cmd: not started")
        
        self.proc.sendline(cmd)
        
        if self.proc.expect(self.prompt) != 0:
            # todo: raise error
            return CmdResult(1, "")

        output = self.proc.before.copy()
        
        self.proc.sendline("echo $?")
        if self.proc.expect(self.prompt) != 0:
            # todo: raise error
            return CmdResult(1, "")

        return CmdResult(int(self.proc.before), output.decode("ascii"))
        

    def send_qmp_cmd(self, cmd):
        if cmd not in SUPPORTED_CMDS:
            # todo: raise error
            return
        
        pass


    def stop(self):
        """
        Stops the VM via the QEMU monitor.
        """
        # todo: implement this via qemu monitor
        os.remove(f"{QMP_FIFO_PATH}.in")
        os.remove(f"{QMP_FIFO_PATH}.out")
        pass

    def reset(self):
        """
        Reset the VM to a clean instance.
        """
        pass

    def _check_started(self):
        return self.started and hasattr(self, "proc")

    def _init_qmp(self):
        # todo: read in from the QMP FIFO, validate
        pass

    def _send_qmp(self):
        # called by stop and reset to stop the vm or reload an earlier instance
        pass
    
    def _startup(self):
        # create the FIFOs for QMP control
        os.mkfifo(f"{QMP_FIFO_PATH}.in")
        os.mkfifo(f"{QMP_FIFO_PATH}.out")

        self.proc = pexpect.spawn(self._cmd, self._cmd_args, timeout=60)
        self.started = True
        self.login()

    def _construct_cmd(self):
        self._cmd_args.extend(self._ADDITIONAL_ARGS)

if __name__ == "__main__":
    config = QemuConfig(Arch.ARM, "root", "toor", "../vms/arm")
    q = Qemu(config)