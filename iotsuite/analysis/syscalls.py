import re

from ..utils import logger as mainlog

logger = mainlog.getChild("analysis-syscalls")

class Syscall:
    """
    Class representing a parsed syscall.
    """
    def __init__(self, syscall, params, result, elab):
        self.syscall = syscall
        self.params = params
        self.result = result
        self.elaboration = elab

class SyscallAnalyzer:

    SYSCALL_REGEX = r"([_a-zA-Z0-9]+)\((.*)\) *(= -?[0-9x]+) ?(.*)"

    def __init__(self):
        self.main_regex = re.compile(self.SYSCALL_REGEX)

    def parse_syscalls(self, tracefile):
        """
        Parses all the syscalls made by process spawned by a sample.

        Returns a tuple of (pid, syscalls).
        """
        
        logger.debug(f"parsing syscall trace file '{tracefile}'")
        syscalls = []

        with open(tracefile, "r") as f:
            data = f.read(-1)

        pid = tracefile.split(".")[1]

        res = self.main_regex.findall(data)

        for syscall, paramstr, result, elab in res:
            syscalls.append(Syscall(
                syscall,
                self._extract_params(paramstr),
                self._cleanup_res(result),
                elab.strip()
            ))

        return pid, syscalls

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
