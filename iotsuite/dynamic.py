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

    def __init__(self, netconfig, vmconfig, c2config):
        self.net = Net(netconfig)
        self.vm = Qemu(vmconfig)
        self.cnc = Qemu(c2config)

    def startup(self, iptables_rules=[], vm_ssh=None, c2_ssh=None):
        self.net.setup()

        for rule in iptables_rules:
            self.net.append_iptables(rule)

        self.vm.noninteractive(vm_ssh)
        self.cnc.noninteractive(c2_ssh)

        if not self.vm.config.qmp:
            self.vm.send_qemu_command("loadvm", ["clean"])

    def send_to_vm(self, path):
        client = IoTFTPClient("")
    
    def run(self):
        pass