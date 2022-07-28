import argparse
import sys
import os
import logging
import shutil
from xdg import BaseDirectory

from .orchestrator import Orchestrator
from .config import Config
from .utils import IoTSuiteError, IoTSuiteFormatter
import iotsuite.utils as utils

SUBCMDS = ["full", "dynamic", "static"]

# configuration keys that are also paths.
_PATH_KEYS = [
    "OutputDir",
    "WorkingDir",
    "PluginDir",
    "Image",
    "NicHelper",
    "DHCPConf",
    "UseFile",
]

logger = utils.logger.getChild("main")

class IoTSuite:
    """
    The IoTSuite class.

    Parses command line arguments to determine the action taken,
    determines the configuration file to read from,
    and controls the overall running of the orchestrator.
    """
    def __init__(self, args):
        self.invocation_dir = os.getcwd()
        self.command = args.command
        self.target = os.path.abspath(args.file.rstrip("/"))

        if args.verbose:
            utils.logger.setLevel(logging.DEBUG)
        elif args.quiet:
            utils.logger.setLevel(logging.WARNING)
        else:
            utils.logger.setLevel(logging.INFO)

        logger.debug(f"got args {args}")

        if args.config is not None:
            config = args.config
        else:
            config = f"{BaseDirectory.xdg_config_home}/iotsuite/iotsuite.conf"

        if not os.path.exists(config):
            raise IoTSuiteError(f"no such file or directory: {config}")

        self.config = Config(config)
        self._verify_paths()

        if not os.path.exists(self.target):
            raise IoTSuiteError(f"no such file or directory: {self.target}")

        if os.path.isdir(self.target):
            batch = True
        else:
            batch = False

        self.orchestrator = Orchestrator(self.config, batch=batch)

        # set up the working directory
        working_dir = self.config.GENERAL["WorkingDir"]
        # defaults to $XDG_CACHE_HOME/iotsuite if not found
        if working_dir is None:
            self.working_dir = f"{BaseDirectory.xdg_cache_home}/iotsuite"
            if not os.path_exists(self.working_dir):
                os.mkdir(self.working_dir)
        else:
            self.working_dir = working_dir

        # set up the output directory
        output_dir = self.config.GENERAL["OutputDir"]
        # defaults to 'output' directory in cwd
        if output_dir is None:
            self.output_dir = f"{os.getcwd()}/output"
            if not os.path_exists(self.output_dir):
                os.mkdir(self.output_dir)
        else:
            self.output_dir = output_dir 

    def run(self):
        # set up the working directory
        try:
            working_dir = self.config.GENERAL["WorkingDir"]
        # defaults to $XDH_CACHE_HOME/iotsuite if not found
        except KeyError:
            self.working_dir = f"{BaseDirectory.xdg_cache_home}/iotsuite"
            if not os.path_exists(self.working_dir):
                os.mkdir(self.working_dir)
        else:
            self.working_dir = working_dir

        os.chdir(self.working_dir)
        
        try:
            shutil.copy(self.target, self.working_dir)
        except:
            pass

        self.target = os.path.basename(self.target)

        self.orchestrator.run(self.target, self.command)
        logger.info("Processing retrieved execution traces")
        self.final = self.orchestrator.run_analysis()

        logger.info("Exporting files to output directory")
        self._export_files()

        # cleanup trace directory
        logger.debug("cleaning up working directory")
        for file in os.listdir():
            os.remove(file)

        os.chdir(self.output_dir)

        logger.info("Writing results to JSON")
        # todo: fix the jank
        with open(f"{self.target}_results.json", "w") as f:
            f.write(self.final.export_as_json())

        # handle json and file output here

        os.chdir(self.invocation_dir)

        # handle finalization
        return

    def _export_files(self):
        files = self.orchestrator.dynamic_results
        try:
            export_raw = self.config.GENERAL["ExportRaw"].split(",")
        except KeyError:
            export_raw = ["pcap"]

        if files is not None:
            for file in files.createdfiles:
                try:
                    shutil.copy(file, self.output_dir)
                except:
                    logger.warning(f"Could not copy created file {file}")

            if "pcap" in export_raw or "all" in export_raw:
                try:
                    shutil.copy(files.pcap, self.output_dir)
                except:
                    logger.warning(f"could not copy PCAP file {files.pcap}")

            if "strace" in export_raw or "all" in export_raw:
                for file in files.syscalls:
                    try:
                        shutil.copy(file, self.output_dir)
                    except:
                        logger.warning(f"Could not copy strace file {file}")

    def _verify_paths(self):
        # verify that all paths are valid, and convert them to absolute paths
        for section in self.config:
            for key in _PATH_KEYS:
                _absolutify(section, key)


def _absolutify(section, key):
    if section.has_key(key):
        if not os.path.exists(section[key]):
            raise IoTSuiteError(f"directory or file {section[key]} does not exist")
        elif not os.path.isabs(section[key]):
            section[key] = os.path.abspath(section[key])
    else:
        return

def _construct_parser():
    # todo: make iotsuite fully configurable via command line as well
    args = [sys.argv[0]]
    if len(sys.argv) > 1 and sys.argv[1] not in SUBCMDS:
        args.append("full")
        args.extend(sys.argv[1:])
        sys.argv = args
    elif len(sys.argv) == 1:
        # this is an error condition but we let argparse handle it
        args.append("full")
        sys.argv = args
    
    ap = argparse.ArgumentParser()
    subs = ap.add_subparsers(dest="command")
    subs.default = "full"

    subcmds = {
        "full": subs.add_parser("full"),
        "static": subs.add_parser("static"),
        "dynamic": subs.add_parser("dynamic")
    }

    for name, sub in subcmds.items():
        sub.add_argument("file", type=str)
        sub.add_argument(
            "-c", "--config", action="store",
            help="the configuration file to use")
        sub.add_argument(
            "-v", "--verbose", action="store_true",
            help="extra output to see what's happening")
        sub.add_argument(
            "-q", "--quiet", action="store_true",
            help="restrict output to warnings and errors only")
        sub.add_argument(
            "-s", "--sudo-passwd", action="store",
            help="specify a sudo password to use"
        )

    return ap, subcmds

def main():
    """
    Entry point of the program.
    """

    parser, subs = _construct_parser()
    args = parser.parse_args()

    handler = logging.StreamHandler()
    handler.setFormatter(IoTSuiteFormatter())
    utils.logger.addHandler(handler)

    try:
        iotsuite = IoTSuite(args)
        iotsuite.run()
    except IoTSuiteError as e:
        logger.error(f"{e}")
        sys.exit(1)
