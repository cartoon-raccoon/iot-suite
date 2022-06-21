import subprocess
from subprocess import CalledProcessError
from collections import namedtuple
import logging

from elftools.elf.elffile import ELFFile
import hashlib

logger = logging.getLogger("static")

Strings = namedtuple('Strings', ['offset', 'string'])

class StaticAnalyzer:

    def __init__(self, sample):
        self.set_sample(sample)

    def set_sample(self, sample):
        """
        Sets the sample to run static analysis on.
        """
        self.sample = sample
        self.strings = []
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
        self._parse_strings(output)

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
        pass

    def get_arch(self):
        return self.elf.get_machine_arch()

    def _parse_strings(self, output):
        for s in output.split("\n"):
            if len(s) < 1:
                continue

            res = s.strip().split()
            offset = int(res[0])
            strs = " ".join(res[0:])
            self.strings.append(Strings(offset=offset, string=strs))
        
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