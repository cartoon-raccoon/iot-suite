import logging

from qemu import Qemu, QemuError
from net import Net
from iotftp import IoTFTPClient, ServerError

from config import Config

logger = logging.getLogger("dynamic")

CNC_PRE_COMMANDS = [
    "rm ~/cowrie/var/run/*",
    "cowrie/bin/cowrie start",
    "sudo python3 FakeDNS/fakedns.py -c FakeDns/iotsuite_dns.conf & > fakedns.txt"
    #"./fakedns.py" # this needs to run in the background and redirect to a file
    # we then need to transfer the file out to this machine
]

CNC_POST_COMMANDS = [
    "sudo pkill python3",
    "cowrie/bin/cowrie stop",
]

# the command to start the IoTFTP server, formatted with ip addr and port
IOTFTP_START_CMD = "python iotftp/server.py {} {}"

# the command to start the on-VM analysis script, formatted with file
ANALYSE_SCRIPT_CMD = "python analyse.py {}"

class UnexpectedExit(Exception):
    """
    Raised when a command exits with a non-zero exit code.
    """
    def __init__(self, res):
        self.res = res
    def __str__(self):
        return f"command exited with error code {self.res.exitcode}"

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
        self.ftclient = IoTFTPClient(iftpconf[0], int(iftpconf[1]), iftpconf[2])

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

        except QemuError as e:
            logger.error(f"an error occurred while starting the VMs: {e}")
            self.net.teardown(sudo_passwd)
            self.vm.stop()
            self.cnc.stop()
            raise e
        except Exception as e:
            logger.error(f"an error occurred while setting up: {e}")
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
                raise UnexpectedExit(res)

    def shutdown(self):

        sudo_passwd = self.config.GENERAL["SudoPasswd"]

        logger.debug("debug: running all cnc shutdown commands")
        for cmd in CNC_POST_COMMANDS:
            res = self.cnc.run_cmd(cmd)
            if res.exitcode != 0:
                # don't raise error since we're shutting down the system anyway
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

    def vm_iotftp_server(self):
        """
        Run the IoTFTP server on the sandbox VM.
        """

        ipaddr = self.config.SANDBOX["IpAddr"]
        port = int(self.config.NETWORK["FileTrfPort"])

        iotftp_cmd = IOTFTP_START_CMD.format(ipaddr, port)

        logger.debug(f"running iotftp server with command {iotftp_cmd}")

        self.vm.run_cmd(iotftp_cmd, wait=False)

    def send_to_vm(self, path, dest, setup=False, bye=True):
        """
        Send a file to the VM via IoTFTP.
        """

        if setup:
            self.vm_iotftp_server()

        #todo: move path to temp folder before sending
        try:
            self.ftclient.put(path)
        except ServerError:
            res = self.vm.terminate_existing()
            raise UnexpectedExit(res)

        if bye:
            self.ftclient.bye()
            res = self.vm.wait_existing()
            if res.exitcode != 0:
                raise UnexpectedExit(res)

    def receive_from_vm(self, path, dest, setup=False, bye=True):
        """
        Receive a file from the VM via IoTFTP.
        """

        if setup:
            self.vm_iotftp_server()
        #todo: move from temp folder to dest

        try:
            self.ftclient.get(path)
        except ServerError:
            res = self.vm.terminate_existing()
            raise UnexpectedExit(res)

        if bye:
            self.ftclient.bye()
            res = self.vm.wait_existing()
            if res.exitcode != 0:
                raise UnexpectedExit(res)
    
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
    import sys
    import traceback

    qemulog = logging.getLogger("qemu")
    dynlog = logging.getLogger("dynamic")

    handler = logging.StreamHandler()
    qemulog.setLevel(logging.DEBUG)
    dynlog.setLevel(logging.DEBUG)
    qemulog.addHandler(handler)
    dynlog.addHandler(handler)

    conf = Config("../configs/iotsuite.conf")

    dynamic = DynamicAnalyzer(conf)

    try:
        dynamic.startup()
    except Exception as e:
        logger.error(f"{traceback.print_tb(sys.exc_info()[2])}\n{e}")
        dynamic.net.teardown(conf.GENERAL["SudoPasswd"])
        sys.exit(1)

    try:
        dynamic.vm_iotftp_server()
        dynamic.send_to_vm("notes", "")
    except Exception as e:
        logger.error(f"{traceback.print_tb(sys.exc_info()[2])}\n{e}")

    
    res = dynamic.vm.run_cmd("ls")
    print(res.output)

    # vm_ipaddr = conf.SANDBOX["IpAddr"]
    # iotftp_port = conf.NETWORK["FileTrfPort"]
    # dynamic.vm.run_cmd(IOTFTP_START_CMD.format())
    try:
        dynamic.shutdown()
    except QemuError:
        dynamic.vm.terminate_existing()
        dynamic.shutdown()
