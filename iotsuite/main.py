import argparse

from .orchestrator import Orchestrator
from .config import Config

class IoTSuite:
    def __init__(self, config: Config):
        pass

def _construct_parser():
    ap = argparse.ArgumentParser()
    subs = ap.add_subparsers(dest="subparser_name")

    full = subs.add_parser("full")
    full.add_argument("file", type=str)
    

    return ap

def main():

    parser = _construct_parser()

    args = parser.parse_args()
    pass