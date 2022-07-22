import re
from collections import namedtuple

from ..utils import logger as mainlog

logger = mainlog.getChild("analysis-syscalls")

Syscall = namedtuple("Syscall", ["syscall", "params", "result", "elaboration"])

class SyscallAnalyzer:

    SYSCALL_REGEX = r"([_a-zA-Z0-9]+)\((.*)\) *(= -?[0-9x]+) ?(.*)"

    def __init__(self):
        self.main_regex = re.compile(self.SYSCALL_REGEX)

    def parse_syscalls(self, tracefile):
        syscalls = []

        with open(tracefile, "r") as f:
            data = f.read(-1)

        res = self.main_regex.findall(data)

        for syscall, paramstr, result, elab in res:
            syscalls.append(Syscall(
                syscall=syscall,
                params=self._extract_params(paramstr),
                result=self._cleanup_res(result),
                elaboration=elab.strip()
            ))

        return syscalls

    def _extract_params(self, paramstr):
        if len(paramstr) == 0:
            return []

        ret = []
        
        buf = ""
        in_struct = False
        for c in paramstr:
            if c == "," and not in_struct:
                ret.append(buf.strip())
                buf = ""
            elif c == "{" and not in_struct:
                buf += c
                in_struct = True
            elif c == "}" and in_struct:
                buf += c
                in_struct = False
            else:
                buf += c

        ret.append(buf.strip())

        return ret

    def _cleanup_res(self, res):
        return res[2:]
