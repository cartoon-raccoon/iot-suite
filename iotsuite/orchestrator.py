import sys
import json

from .config import Config
from .dynamic import DynamicAnalyzer
from .static import StaticAnalyzer
import iotsuite.utils as utils
from .utils import IoTSuiteError
from .analysis import syscalls, net

logger = utils.logger.getChild("orchestrator")

class AnalysisResult:
    """
    A serializable class that holds the full results of the analysis.

    This class be serialized into JSON or pickled using the `pickle` package.

    This allows the results of the sandbox analysis to be consumed by a generic
    front-end interface that can deserialize JSON or pickle data.
    """
    def __init__(self, **plugin_results):
        for mod, res in plugin_results.items():
            setattr(self, mod, res)

    def __getitem__(self, item):
        return self.__dict__[item]

    def __setitem__(self, key, item):
        setattr(self, key, item)

    def add_new_result(self, mod, res):
        """
        Add the new results of an analysis module to the Results.
        """
        setattr(self, mod, res)

    def export_as_json(self):
        # todo: fix the jank
        return json.dumps(self, 
            default=lambda o: o.__dict__, 
            sort_keys=False,
            indent=4
        )

    def export_as_pickle(self):
        utils.todo()

class Orchestrator:
    def __init__(self, config: Config, **params):
        self.config = config
        self.net_analyzer = net.NetAnalyzer()
        self.syscalls = syscalls.SyscallAnalyzer()

        try: # todo: more robust code, please
            self.disallowed = config.GENERAL["DisallowArchs"].split(",")
        except KeyError:
            self.disallowed = []

        if "batch" in params and params["batch"]:
            self.batch = True
        else:
            self.batch = False
        
        self.static = StaticAnalyzer(self.config)

    def __enter__(self):
        # startup and initialize the static and dynamic analysers
        pass

    def __exit__(self):
        # shutdown the static and dynamic analysers
        pass

    def run(self, sample, command):
        if self.batch:
            self.run_batch(sample, command)
        else:
            self.run_single(sample, command)

    def run_batch(self, samples, command):
        # run on a batch
        logger.debug(f"running batch on dir {samples}")
        utils.todo()

    def run_single(self, sample, command):
        self.static.set_sample(sample)
        arch = self.static.get_arch_enum()

        if arch.value in self.disallowed:
            raise IoTSuiteError(f"architecture {arch.value} is currently disallowed")
        
        if command != "dynamic":
            self.staticres = self.run_static(sample)
        
        if command != "static":
            self.dynamicres = self.run_dynamic(sample)

        # todo: run analysis

    def run_static(self, sample):
        logger.debug("running static analysis")

        self.static.set_sample(sample)
        return self.static.run()

    def run_dynamic(self, sample):
        logger.debug("running dynamic analysis")

        self.static.set_sample(sample)
        arch = self.static.get_arch_enum()

        logger.info(
            f"Sample has architecture {self.static.get_arch_enum().value}"
        )
        try:
            self.dynamic = DynamicAnalyzer(arch, self.config)
        except Exception as e:
            raise IoTSuiteError(f"{e}")

        try:
            self.dynamic.startup()
            res = self.dynamic.run(sample)
            logger.debug(f"{res}")
        except KeyboardInterrupt:
            logger.warning("Received Ctrl-C, stopping...")
            sys.exit(0)
        except IoTSuiteError as e:
            raise e
        except Exception as e:
            raise IoTSuiteError(f"{e}")
        finally:
            self.dynamic.shutdown()

        return res

    def run_analysis(self):
        final = AnalysisResult()

        if self._was_completed("static"):
            final["static"] = self.staticres

        if self._was_completed("dynamic"):
            logger.debug("running dynamic results analysis")

            final["start"] = self.dynamicres.start
            final["end"] = self.dynamicres.end

            # run syscall analysis
            syscalls = dict()

            # trace is a path, so it will be affected if we change dir
            # assume trace is in our current working directory
            for trace in self.dynamicres.syscalls:
                pid, syscall = self.syscalls.parse_syscalls(trace)
                syscalls[pid] = syscall

            final["syscalls"] = syscalls
            final["createdfiles"] = self.dynamicres.createdfiles

            net = self.net_analyzer.get_result(
                self.dynamicres.pcap,
                self.dynamicres.dnsoutput
            )
            final["dns"] = net.dns
            # todo: parse packets

        return final

    @property
    def dynamic_results(self):
        if self._was_completed("dynamic"):
            return self.dynamicres
        else:
            return None

    @property
    def static_results(self):
        if self._was_completed("static"):
            return self.staticres
        else:
            return None


    def run_plugins(self):
        utils.todo()

    def _was_completed(self, ty):
        """
        Returns whether the analysis was completed and the results are stored.
        """
        return hasattr(self, f"{ty}res")


if __name__ == "__main__":
    pass