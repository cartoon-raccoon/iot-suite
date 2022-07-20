import sys
import logging

logger = logging.getLogger()

formatter = logging.Formatter()
debug_formatter = logging.Formatter("%(funcName)s: %(msg)s")

class IoTSuiteError(Exception):
    
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg

    def __repr__(self):
        return f"IoTSuiteError('{self.msg}')"

def todo():
    _die_horribly("the idiot who wrote this code left it unfinished.", 69)

def unreachable():
    _die_horribly("the impossible has happened, and we've reached the backrooms.", 420)

def _die_horribly(msg, code):
    logger.critical(msg)
    sys.exit(code)