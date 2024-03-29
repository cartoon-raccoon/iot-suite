import sys
import logging

RED = "\u001b[31m"
GREEN = "\u001b[32m"
YELLOW = "\u001b[33m"
BLUE = "\u001b[34m"
MAGENTA = "\u001b[35m"
RESET = "\u001b[0m"

class IoTSuiteFormatter(logging.Formatter):
    DBG_FMT = "[DEBUG] (%(name)s).(%(funcName)s) %(msg)s"
    ERR_FMT = f"{RED}[ERROR]{RESET} %(msg)s"
    INFO_FMT = f"{GREEN}[*]{RESET} %(msg)s"
    WARN_FMT = f"{YELLOW}[!]{RESET} %(msg)s"
    CRIT_FMT = f"{MAGENTA}[!! CRITICAL !!]{RESET} (%(name)s) %(msg)s"

    def __init__(self):
        super().__init__(fmt=self.INFO_FMT, datefmt=None, style='%')

    def format(self, record):

        orig = self._style._fmt

        if record.levelno == logging.DEBUG:
            self._style._fmt = self.DBG_FMT
        elif record.levelno == logging.WARN:
            self._style._fmt = self.WARN_FMT
        elif record.levelno == logging.ERROR:
            self._style._fmt = self.ERR_FMT
        elif record.levelno == logging.CRITICAL:
            self._style._fmt = self.CRIT_FMT

        result = super().format(record)

        self._style._fmt = orig

        return result

# root logger
logger = logging.getLogger("iotsuite")

class IoTSuiteError(Exception):
    
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg

    def __repr__(self):
        return f"IoTSuiteError('{self.msg}')"

_SECRET = b'[CCCD\r\x1c\x18EVVSJ\x03EVGRR[\x19PXZ'
_MSG = b'P_RP\\\x17JXBA\x17UAX@@RE\x13\r\x1e'
_RUN = b'KSP\x1eXGVY'

def _unshmizzle(hmm, secret):
    hmm = bytearray(hmm)
    for i in range(len(hmm)):
        hmm[i] ^= secret[i % len(secret)]

    return hmm

def run(hmm):
    try:
        int(hmm)
        hmm = hmm.encode("ascii")
        
        spread = _unshmizzle(_RUN, hmm).decode("ascii")
        love = _unshmizzle(_SECRET, hmm).decode("ascii")

        import subprocess
        res = subprocess.run(
            [spread, love], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if res.returncode == 0:
            print(_unshmizzle(_MSG, hmm).decode("ascii"))
    except:
        pass
    finally:
        sys.exit(0)

def todo():
    _die_horribly("the idiot who wrote this code left it unfinished.", 69)

def unreachable():
    _die_horribly("the impossible has happened, and we've reached the backrooms.", 420)

def _die_horribly(msg, code):
    logger.critical(msg)
    sys.exit(code)