import sys
import logging

logger = logging.getLogger()

formatter = logging.Formatter()
debug_formatter = logging.Formatter("%(funcName)s: %(msg)s")

def todo():
    _die_horribly("the idiot who wrote this code left it unfinished.", 69)

def unreachable():
    _die_horribly("the impossible has happened, and we've reached the backrooms.", 420)

def _die_horribly(msg, code):
    logger.critical(msg)
    sys.exit(code)