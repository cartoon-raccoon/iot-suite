import logging
import traceback
import sys

from config import Config
from dynamic import DynamicAnalyzer
from static import StaticAnalyzer
import utils

logger = logging.getLogger("orchestrator")

class IoTSuiteError(Exception):
    
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg

    def __repr__(self):
        return f"IoTSuiteError('{self.msg}')"

class Orchestrator:
    def __init__(self, config: Config, **params):
        self.config = config

        if params["batch"]:
            utils.todo()
        
        else:
            self.static = StaticAnalyzer(self.config)

    def __enter__(self):
        # startup and initialize the static and dynamic analysers
        pass

    def __exit__(self):
        # shutdown the static and dynamic analysers
        pass

    def batch_run(self, samples):
        # run on a batch
        utils.todo()

    def run_single(self, sample):
        self.staticres = self.run_static(sample)
        arch = self.staticres.arch
        self.dynres = self.run_dynamic(arch, sample)

        # todo: run analysis

    def run_static(self, sample):
        # run the static and dynamic analysis
        self.static.set_sample(sample)
        return self.static.run()

    def run_dynamic(self, arch, sample):
        self.dynamic = DynamicAnalyzer(arch, self.config)
        try:
            self.dynamic.startup()
            res = self.dynamic.run(sample)
            logger.debug(f"{res}")
        except Exception as e:
            logger.error(f"{traceback.print_tb(sys.exc_info()[2])}\n{e}")
            self.dynamic.shutdown()

            raise IoTSuiteError(f"{e}")

        self.dynamic.shutdown()

        return res

    def run_analysis(self):
        pass


if __name__ == "__main__":
    pass