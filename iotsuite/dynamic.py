import logging

from qemu import Qemu
from net import Net
from iotftp import IoTFTPClient

from config import Config

logger = logging.getLogger("dynamic")

CNC_PRE_COMMANDS = [
    "cowrie/bin/cowrie start",
    "sudo python3 FakeDNS/fakedns.py -c FakeDns/iotsuite_dns.conf & > fakedns.txt"
    #"./fakedns.py" # this needs to run in the background and redirect to a file
    # we then need to transfer the file out to this machine
]

CNC_POST_COMMANDS = [
    "sudo pkill python3",
]

# the command to start the IoTFTP server, formatted with ip addr and port
IOTFTP_START_CMD = "python iotftp/server.py {} {}"

# the command to start the on-VM analysis script, formatted with file
ANALYSE_SCRIPT_CMD = "python analyse.py {}"

class UnexpectedExit(Exception):
    def __init__(self, errcode, stderr):
        self.exitcode = errcode
        self.stderr = stderr

    def __str__(self):
        return f"command exited with error code {self.exitcode}"

class DynamicAnalyzer:
    """
    Initializes, starts up, and manages the network and the CNC & sandbox QEMU VMs.
    """

    # vmconfig and c2config should be QemuConfig
    def __init__(self, config: Config):
        netconfig = config.network
        vmconfig = config.sandbox(Arch.ARM)
        c2config = config.cnc

        self.config = config

        iftpconf = (
            config.SANDBOX["IpAddr"],
            config.NETWORK["FileTrfPort"],
            config.NETWORK["TrfEncoding"],
        )
        self.net = Net(netconfig)
        self.vm = Qemu(vmconfig)
        self.cnc = Qemu(c2config)
        # [0] is ip addr, [1] is port, [2] is encoding
        self.ftclient = IoTFTPClient(iftpconf[0], iftpconf[1], iftpconf[2])

    def startup(self):
        sudo_passwd = self.config.GENERAL["SudoPasswd"]
        iptables_rules = self.config.iptables()
        # set up the network
        logger.debug("debug: setting up network")
        self.net.setup(sudo_passwd)

        logger.debug("debug: adding iptables rules")
        for rule in iptables_rules:
            self.net.append_iptables(rule)

        if self.config.SANDBOX.ssh():
            vm_ssh = (self.config.SANDBOX["IpAddr"], int(self.config.SANDBOX["SSHPort"]))
        else:
            vm_ssh = None

        if self.config.CNC.ssh():
            c2_ssh = (self.config.CNC["IpAddr"], int(self.config.CNC["SSHPort"]))
        else:
            c2_ssh = None

        try:
            # startup the vms
            logger.debug("debug: starting noninteractive vm session")
            self.vm.noninteractive(vm_ssh)
            logger.debug("debug: starting noninteractive c2 session")
            self.cnc.noninteractive(c2_ssh)
        except Exception as e:
            logger.error(f"an error occurred while starting the VMs: {e}")
            self.net.teardown(sudo_passwd)
            raise e

        # reset the sandbox to a clean state
        if not self.vm.config.qmp:
            logger.debug("debug: resetting VM to clean state")
            self.vm.reset("clean")

        logger.debug("debug: running cnc pre-analysis commands")
        for cmd in CNC_PRE_COMMANDS:
            logger.debug(f"debug: running command '{cmd}'")
            res = self.cnc.run_cmd(cmd)
            if res.exitcode != 0:
                logger.error(f"command '{cmd}' returned exitcode {res.exitcode}, errmsg '{res.output}'")
                raise UnexpectedExit(res.exitcode, res.output)

    def shutdown(self):

        sudo_passwd = self.config.GENERAL["SudoPasswd"]

        logger.debug("debug: running all cnc shutdown commands")
        for cmd in CNC_POST_COMMANDS:
            res = self.cnc.run_cmd(cmd)
            if res.exitcode != 0:
                logger.error(f"command '{cmd}' returned exitcode {res.exitcode} errmsg '{res.output}'")

        # shutdown the sandbox and cnc VMs
        logger.debug("debug: stopping sandbox vm")
        self.vm.stop()
        logger.debug("debug: stopping c2 vm")
        self.cnc.stop()

        # flush iptables
        logger.debug("debug: flushing iptables")
        self.net.flush_iptables(sudo_passwd)

        logger.debug("tearing down network infrastructure")
        self.net.teardown(sudo_passwd)


    def send_to_vm(self, path, dest, bye=True):
        #todo: move dest to temp folder
        self.ftclient.put(path)

        if bye:
            self.ftclient.bye()

    def receive_from_vm(self, path, dest, bye=True):
        #todo: move from temp folder to dest
        #! setting bye to true assumes that the server is already running
        self.ftclient.get(path)

        if bye:
            self.ftclient.bye()
    
    def run(self, sample_path):
        # todo:
        #* 1. send sample to vm via iotftp
        #* 2. run analyse.py
        #* 3. collate list of files to retrieve
        #* 4. retrieve files from sandbox vm
        #* 5. retrieve dns record from cnc vm
        pass

if __name__ == "__main__":
    from config import Config
    from arch import Arch

    handler = logging.StreamHandler()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    conf = Config("../configs/iotsuite.conf")

    dynamic = DynamicAnalyzer(conf)

    dynamic.startup()

    # vm_ipaddr = conf.SANDBOX["IpAddr"]
    # iotftp_port = conf.NETWORK["FileTrfPort"]
    # dynamic.vm.run_cmd(IOTFTP_START_CMD.format())
    dynamic.shutdown()
