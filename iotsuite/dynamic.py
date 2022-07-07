import logging

from qemu import Qemu
from net import Net
from iotftp import IoTFTPClient

from config import Config

logger = logging.getLogger("dynamic")

CNC_PRE_COMMANDS = [
    "cowrie/bin/cowrie start",
    #"./fakedns.py" # this needs to run in the background and redirect to a file
    # we then need to transfer the file out to this machine
]

CNC_POST_COMMANDS = []

# the command to start the IoTFTP server, formatted with ip addr and port
IOTFTP_START_CMD = "python iotftp/server.py {} {}"

# the command to start the on-VM analysis script, formatted with file
ANALYSE_SCRIPT_CMD = "python analyse.py {}"

class DynamicAnalyzer:
    """
    Initializes, starts up, and manages the network and the CNC & sandbox QEMU VMs.
    """

    # vmconfig and c2config should be QemuConfig
    def __init__(self, netconfig, vmconfig, c2config, iotftpconfig):
        self.net = Net(netconfig)
        self.vm = Qemu(vmconfig)
        self.cnc = Qemu(c2config)
        # [0] is ip addr, [1] is port, [2] is encoding
        self.ftclient = IoTFTPClient(iotftpconfig[0], iotftpconfig[1], iotftpconfig[2])

    def startup(self, sudo_passwd, iptables_rules=[], vm_ssh=None, c2_ssh=None):
        # set up the network
        logger.debug("debug: setting up network")
        self.net.setup(sudo_passwd)

        logger.debug("debug: adding iptables rules")
        for rule in iptables_rules:
            self.net.append_iptables(rule)

        # startup the vms
        logger.debug("debug: starting noninteractive vm session")
        self.vm.noninteractive(vm_ssh)
        logger.debug("debug: starting noninteractive c2 session")
        self.cnc.noninteractive(c2_ssh)

        # reset the sandbox to a clean state
        if not self.vm.config.qmp:
            logger.debug("debug: resetting VM to clean state")
            self.vm.reset("clean")

        logger.debug("debug: running cnc pre-analysis commands")
        for cmd in CNC_PRE_COMMANDS:
            logger.debug(f"debug: running command '{cmd}'")
            res = self.cnc.run_cmd(cmd)
            if res.exitcode != 0:
                #todo: raise error
                logger.error(f"command '{cmd}' returned with exitcode {res.exitcode}, errmsg '{res.output}'")

    def shutdown(self, sudo_passwd):

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
        self.ftclient.get(path)

        if bye:
            self.ftclient.bye()
    
    def run(self, sample_path):
        # todo:
        #* 1. send sample to vm via iotftp
        #* 2. run analyse.py
        #* 3. collate list of files to retrieve
        #* 4. retrieve files
        pass

if __name__ == "__main__":
    from config import Config
    from arch import Arch

    handler = logging.StreamHandler()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    conf = Config("../configs/iotsuite.conf")

    sudo = conf.GENERAL["SudoPasswd"]

    net_cf = conf.network
    vm_qemucf = conf.sandbox(Arch.ARM)
    c2_qemucf = conf.cnc

    if conf.CNC.ssh():
        c2_ssh = (conf.CNC["IpAddr"], int(conf.CNC["SSHPort"]))

    iftpconf = (
        conf.SANDBOX["IpAddr"],
        conf.NETWORK["FileTrfPort"],
        conf.NETWORK["TrfEncoding"],
    )

    dynamic = DynamicAnalyzer(
        net_cf, vm_qemucf, c2_qemucf, iftpconf
    )

    dynamic.startup(sudo, c2_ssh=c2_ssh)
    dynamic.shutdown(sudo)
