import logging

from qemu import Qemu
from net import Net
from iotftp import IoTFTPClient

logger = logging.getLogger("dynamic")

CNC_PRE_COMMANDS = [
    "bin/cowrie start"
    "./fakedns.py" # this needs to run in the background and redirect to a file
    # we then need to transfer the file out to this machine
]

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

    def startup(self, iptables_rules=[], vm_ssh=None, c2_ssh=None):
        # set up the network
        self.net.setup()

        for rule in iptables_rules:
            self.net.append_iptables(rule)

        # startup the vms
        self.vm.noninteractive(vm_ssh)
        self.cnc.noninteractive(c2_ssh)

        # reset the sandbox to a clean state
        if not self.vm.config.qmp:
            self.vm.send_qemu_command("loadvm", ["clean"])

        for cmd in CNC_PRE_COMMANDS:
            res = self.cnc.run_cmd(cmd)
            if res.exitcode != 0:
                #todo: raise error
                logger.error(f"command {cmd} returned with exitcode {res.exitcode}, errmsg '{res.output}'")

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

    conf = Config("../configs/iotsuite.conf")

    vm_ip = conf.SANDBOX["IpAddr"]
    vm_port = conf.SANDBOX["Port"]
