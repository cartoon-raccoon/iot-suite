from config import Config

class Orchestrator:
    def __init__(self, config: Config, **params):
        self.config = config

    def __enter__(self):
        # startup and initialize the static and dynamic analysers
        pass

    def __exit__(self):
        # shutdown the static and dynamic analysers
        pass

    def batch_run(self, samples):
        # run on a batch
        pass

    def run_single(self, sample):
        self.run_static(sample)
        self.run_dynamic(sample)

    def run_static(self, sample):
        # run the static and dynamic analysis
        pass

    def run_dynamic(self, sample):
        pass