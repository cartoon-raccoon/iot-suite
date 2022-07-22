import subprocess
from subprocess import CalledProcessError
from collections import namedtuple
import logging

from elftools.elf.elffile import ELFFile
import magic
import hashlib

from .arch import *
from .config import Config
import iotsuite.utils as utils
from .utils import IoTSuiteError

logger = utils.logger.getChild("static")

Strings = namedtuple('Strings', ['offset', 'string'])

StaticResult = namedtuple("StaticResult", [
    "hash", "ctph", "strings", "arch", "file"
])

class StaticError(IoTSuiteError):
    
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg

    def __repr__(self):
        return f"StaticError('{self.msg}')"

class StaticAnalyzer:

    def __init__(self, config: Config):
        self.config = config
        self.magic = magic.Magic()

    def set_sample(self, sample):
        """
        Sets the sample to run static analysis on.
        """
        self.sample = sample
        self.elf = ELFFile(open(sample, "rb"))
        
        with open(sample, "rb") as f:
            self.data = f.read(-1)

    def run_strings(self):
        """
        Run `strings` on the sample and retrieve any strings
        """
        strings_args = ["strings", "-t", "d", self.sample]
        try:
            res = subprocess.run(strings_args, 
                capture_output=True, check=True)
        except CalledProcessError as e:
            pass #todo error handling

        output = res.stdout.decode("utf-8")
        return self._parse_strings(output)

    def run_hash(self):
        hash = self.config.STATIC["HashType"]

        if hash.lower() == "sha256":
            return self.sha256()
        elif hash.lower() == "md5":
            return self.md5()
        else:
            raise StaticError(f"unknown hash type: {hash}")

    def sha256(self):
        """
        Get the SHA256 hash of the sample.
        """
        hash = hashlib.sha256(self.data)
        return hash.digest()

    def md5(self):
        """
        Get the MD5 hash of the sample.
        """
        hash = hashlib.md5(self.data)
        return hash.digest()

    def check_upx(self):
        # todo: check entropy and search for UPX magic
        # if entropy is high but UPX magic is not present, packing
        # may still be present but UPX magic is stripped
        utils.todo()

    def run_ctph(self):
        # todo
        utils.todo()

    def get_arch(self):
        return self.elf.get_machine_arch()

    def get_arch_enum(self):
        arch = self.get_arch()
        if arch == ARM:
            return Arch.ARM
        elif arch == MIPS:
            if self.elf.little_endian:
                return Arch.MIPSEL
            else:
                return Arch.MIPS
        elif arch == M68K:
            return Arch.M68K
        elif arch == PPC:
            return Arch.PPC
        elif arch == I386:
            return Arch.I386
        elif arch == AMD64:
            return Arch.AMD64

    def get_file(self):
        return self.magic.from_file(self.sample)

    def run(self):
        return StaticResult(
            hash=self.run_hash(),
            ctph=None, #todo
            strings=self.run_strings(),
            arch=self.get_arch_enum(),
            file=self.get_file()
        )

    def _parse_strings(self, output):
        ret = []
        for s in output.split("\n"):
            if len(s) < 1:
                continue

            res = s.strip().split()
            offset = int(res[0])
            strs = " ".join(res[1:])
            ret.append(Strings(offset=offset, string=strs))

        return ret
        
    def _check_packing(self):
        pass

if __name__ == "__main__":
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    static = StaticAnalyzer("./testelf")
    static.run_strings()
    print(static.strings)
    print(static.sha256())
    print(static.get_arch())