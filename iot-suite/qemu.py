import pexpect
import logging
import shutil

from .arch import Arch, ARCH_CMDS

USER_PROMPT = "$"
ROOT_PROMPT = "#"

logger = logging.getLogger()

class QemuConfig:
    
    def __init__(self, arch: Arch, user, passwd, image):
        self.arch = arch
        self.user = user
        self.passwd = passwd
        self.image = image


class Qemu:
    _ADDITIONAL_ARGS = ["-nographic",
        "-serial", "stdio",
        "-chardev", "pipe,id=mon0,path=/tmp/guest",
        "-mon", "chardev=mon0,mode=control",
    ]
    
    def __init__(self, config):
        self.config = config
        self.started = False

        # construct the command to execute
        vmdir, kern = self.config.image, f"{self.config.image}/kernel.img"
        self._cmd = shutil.which(ARCH_CMDS[self.config.arch])
        self._cmd_args = self.config.arch.args(vmdir, kern)

    def interactive(self):
        pass

    def noninteractive(self):
        pass

    def login(self):
        pass

    def run_cmd(self):
        pass

    def stop(self):
        # todo: implement this via qemu monitor
        pass

    def _startup(self):
        self.proc = pexpect.spawn(self._cmd, self._cmd_args, timeout=None)
        pass

    def _construct_cmd(self):
        self._cmd_args.extend(self._ADDITIONAL_ARGS)