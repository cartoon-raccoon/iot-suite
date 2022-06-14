import subprocess
from subprocess import CalledProcessError
from collections import namedtuple

from elftools.elf.elffile import ELFFile
import hashlib

Strings = namedtuple('Strings', ['offset', 'string'])

class StaticAnalyzer:
    strings_args = ["strings", "-t", "d"]

    def __init__(self, sample):
        self.set_sample(sample)

    def set_sample(self, sample):
        self.sample = sample
        self.strings = []
        self.elf = ELFFile(open(sample, "rb"))
        
        with open(sample, "rb") as f:
            self.data = f.read(-1)

    def run_strings(self):
        try:
            res = subprocess.run(self.strings_args, 
                capture_output=True, check=True)
        except CalledProcessError as e:
            pass #todo error handling

        output = res.stdout.decode("utf-8")
        self._parse_strings(output)

    def sha256(self):
        hash = hashlib.sha256(self.data)
        return hash.digest()

    def md5(self):
        hash = hashlib.md5(self.data)
        return hash.digest()

    def get_arch(self):
        return self.elf.get_machine_arch()

    def _parse_strings(self, output):
        for s in output.split("\n"):
            res = s.strip().split()
            offset = int(res[0])
            strs = " ".join(res[0:])
            self.strings.append(Strings(offset=offset, string=strs))
        
    def _check_packing(self):
        pass