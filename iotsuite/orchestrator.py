import logging
import traceback
import sys

from .config import Config
from .dynamic import DynamicAnalyzer
from .static import StaticAnalyzer
import iotsuite.utils as utils
from .utils import IoTSuiteError
from .analysis import syscalls, net

logger = logging.getLogger("orchestrator")

class AnalysisResult:
    """
    A JSON-serializable class that holds the full results of the analysis.
    """
    def __init__(self, **plugin_results):
        for mod, res in plugin_results:
            setattr(self, mod, res)

    def __getitem__(self, item):
        return self.__dict__[item]

class Orchestrator:
    def __init__(self, config: Config, **params):
        self.config = config
        self.net_analyzer = net.NetAnalyzer()
        self.syscalls = syscalls.SyscallAnalyzer()

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
        try: # todo: better error handling my god
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

    def run_plugins(self):
        pass


if __name__ == "__main__":
    pass