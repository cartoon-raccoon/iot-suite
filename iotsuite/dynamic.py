import re
from collections import namedtuple

from .qemu import Qemu, QemuError
from .net import Net
from .iotftp import IoTFTPClient, ServerError
from .utils import IoTSuiteError
import iotsuite.utils as utils
from .arch import Arch
from .config import Config

logger = utils.logger.getChild("dynamic")

# namedtuple for things
Cmd = namedtuple("Cmd", ["cmd", "wait"])

CNC_PRE_COMMANDS = [
    Cmd(cmd="rm ~/cowrie/var/run/*", wait=True),
    Cmd(cmd="cowrie/bin/cowrie start", wait=True),
]

CNC_POST_COMMANDS = [
    #"sudo pkill python3",
    Cmd(cmd="cowrie/bin/cowrie stop", wait=True),
]

FAKEDNS_CMD = Cmd(cmd="sudo python3 FakeDns/fakedns.py -c {}", wait=False)

# the command to start the IoTFTP server, formatted with ip addr and port
IOTFTP_START_CMD = "python iotftp/server.py {} {}"

# the command to start the on-VM analysis script, formatted with file
ANALYSE_SCRIPT_CMD = "python analyse.py {}"
# the command to set the execute permission on the sample, formatted with filename
SET_PERMS_CMD = "chmod u+x {}"
FILE_LIST_START = "===== LIST OF FILES TO RETRIEVE ====="
FILE_LIST_END = "===== END LIST ====="

class UnexpectedExit(IoTSuiteError):
    """
    Raised when a command exits with a non-zero exit code.
    """
    def __init__(self, res):
        self.res = res
    def __str__(self):
        return f"command exited with error code {self.res.exitcode}"

# dnsoutput - the output string from the fakedns server
# syscalls - the list of files generated by strace
# createdfiles - the list of files created by the sample
DynamicResult = namedtuple("DynamicResult", [
    "dnsoutput", "syscalls", "pcap", "createdfiles"
])

class DynamicAnalyzer:
    """
    Initializes, starts up, and manages the network and the CNC & sandbox QEMU VMs.
    """

    # vmconfig and c2config should be QemuConfig
    def __init__(self, arch: Arch, config: Config):
        netconfig = config.network
        vmconfig = config.sandbox(arch)
        c2config = config.cnc

        self.config = config

        # todo: perform check that none of these fields are None
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
        """
        Starts the network infrastructure, as well as the sandbox and CNC VMs.
        """
        
        try:
            sudo_passwd = self.config.GENERAL["SudoPasswd"]
        except KeyError:
            logger.warn("no sudo password provided, some commands may fail!")
            sudo_passwd = ""

        iptables_rules = self.config.iptables()
        # set up the network
        logger.info("Setting up network")
        self.net.setup(sudo_passwd)

        logger.info("Adding iptables rules")
        for rule in iptables_rules:
            self.net.append_iptables(rule)

        if self.config.SANDBOX.ssh:
            vm_ssh = (self.config.SANDBOX["IpAddr"], int(self.config.SANDBOX["SSHPort"]))
        else:
            vm_ssh = None

        if self.config.CNC.ssh:
            c2_ssh = (self.config.CNC["IpAddr"], int(self.config.CNC["SSHPort"]))
        else:
            c2_ssh = None

        #? how will this affect when running in batches?
        if self.vm.needs_offline_reset():
            self.vm.offline_snapshot("clean")

        try:
            # startup the vms
            logger.debug("starting noninteractive vm session")
            logger.info("Starting sandbox VM")
            self.vm.noninteractive(vm_ssh)
            logger.debug("starting noninteractive c2 session")
            logger.info("Starting FakeC2 VM")
            self.cnc.noninteractive(c2_ssh)

        except QemuError as e:
            logger.error(f"an error occurred while starting the VMs: {e}")
            self.net.teardown(sudo_passwd)
            self.vm.stop(force=True)
            self.cnc.stop(force=True)
            raise e
        except Exception as e:
            logger.error(f"an error occurred while setting up: {e}")

        if not self.vm.config.qmp and not self.vm.needs_offline_reset():
            logger.debug("taking vm snapshot")
            self.vm.snapshot("clean")

        logger.debug("running cnc pre-analysis commands")
        logger.info("Preparing C2 VM for dynamic analysis")
        for cmd in CNC_PRE_COMMANDS:
            logger.debug(f"running command '{cmd}'")
            res = self.cnc.run_cmd(cmd.cmd, wait=cmd.wait)
            if res.exitcode != 0:
                logger.error(f"command '{cmd}' returned exitcode {res.exitcode}, errmsg '{res.output}'")
                raise UnexpectedExit(res)

    def shutdown(self):
        """
        Shuts down the network infrastructure and VMs.
        """
        logger.info("Shutting down infrastructure...")

        sudo_passwd = self.config.GENERAL["SudoPasswd"]

        logger.debug("running all cnc shutdown commands")
        logger.info("Preparing C2 VM for shutdown")
        for cmd in CNC_POST_COMMANDS:
            try:
                res = self.cnc.run_cmd(cmd.cmd, wait=cmd.wait)

                if res.exitcode != 0:
                    # don't raise error since we're shutting down the system anyway
                    logger.error(f"command '{cmd}' exited with {res.exitcode}, errmsg '{res.output}'")
            except QemuError:
                pass
        
        logger.debug("resetting sandbox vm")
        
        # if our vm doesn't need an offline reset, run the reset live
        if not self.vm.needs_offline_reset():
            self.vm.reset("clean")

        try: # shutdown the sandbox and cnc VMs
            logger.info("Stopping sandbox VM")
            self.vm.stop(force=True)
            logger.info("Stopping FakeC2 VM")
            self.cnc.stop(force=True)
        except QemuError:
            self.vm.terminate_existing()
            self.cnc.terminate_existing()

        # if our vm needs offline reset, do it now
        if self.vm.needs_offline_reset():
            self.vm.offline_reset("clean")

        logger.info("Shutting down network")
        # flush iptables
        logger.debug("flushing iptables")
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

        Setting `setup` to `True` will run `vm_iotftp_server` before sending the file.
        `bye` controls whether a `BYE` command will be sent after sending the file.
        """

        if setup:
            self.vm_iotftp_server()

        #todo: move path to temp folder before sending
        try:
            self.ftclient.put(path)
        except ServerError as e:
            logger.error(f"received error while attempting to send to vm: {e}")
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

        Setting `setup` to `True` will run `vm_iotftp_server` before sending the file.
        `bye` controls whether a `BYE` command will be sent after sending the file.
        """

        if setup:
            self.vm_iotftp_server()
        #todo: move from temp folder to dest

        try:
            self.ftclient.get(path)
        except ServerError as e:
            #! FIXME: this doesn't actually fix some issues
            logger.error(f"received error while attempting to send to vm: {e}")
            res = self.vm.terminate_existing()
            raise UnexpectedExit(res)

        if bye:
            self.ftclient.bye()
            res = self.vm.wait_existing()
            if res.exitcode != 0:
                raise UnexpectedExit(res)
    
    def run(self, sample):
        """
        Transfers the sample to the sandbox VM, starts the fake DNS server on the
        CNC VM, and runs the analysis script on the sandbox VM.

        The analysis script will output the files produced, and the files will then
        be retrieved from the sandbox VM via IoTFTP, and sorted into created files,
        packet capture files, and syscall traces.
        """
        # set up iotftp server and send sample over
        logger.info("Loading sample onto sandbox VM")
        try:
            self.vm_iotftp_server()
            self.send_to_vm(sample, "")
        except Exception as e:
            logger.error(f"{traceback.print_tb(sys.exc_info()[2])}\n{e}")

        # set permissions to execute the sample
        res = self.vm.run_cmd(SET_PERMS_CMD.format(sample))
        # setup fakedns on the CNC
        res = self.cnc.run_cmd( #todo: soft-code the config file string
            FAKEDNS_CMD.cmd.format("FakeDns/iotsuite_dns.conf"),
            wait=FAKEDNS_CMD.wait,
        )
        # run the analysis script
        logger.info("Starting analysis...")
        res = self.vm.run_cmd(ANALYSE_SCRIPT_CMD.format(sample))
        # terminate fakedns on the cnc
        cncres = self.cnc.terminate_existing("python3")

        logger.debug(f"output from fakedns: {cncres.output}")

        result_files = self._extract_files(res.output)

        # todo: better logging of errors. PLEASE.
        logger.info("Retrieving execution traces and files from VM")
        try:
            self.vm_iotftp_server()
            for file in result_files:
                logger.info(f"Retrieving file: {file}")
                try:
                    self.receive_from_vm(file, "", bye=False)
                except Exception as e:
                    logger.error(f"{traceback.print_tb(sys.exc_info()[2])}\n{e}")
            self.ftclient.bye()
            self.vm.wait_existing()
        except Exception as e:
            logger.error(f"{traceback.print_tb(sys.exc_info()[2])}\n{e}")

        usef = sample[:8] if len(sample) > 8 else sample

        pcap = f"{usef}.pcapng"

        traces, created = self._sort_files(usef, result_files)

        return DynamicResult(
            dnsoutput=cncres.output,
            syscalls=traces,
            pcap=pcap,
            createdfiles=created
        )

        

    def _sort_files(self, usef, files):
        
        stracefile_re = re.compile(f"^strace_{usef}\.[0-9]+$")

        stracefiles = []
        createdfiles = []

        for file in filter(lambda s: stracefile_re.match(s) is not None, files):
            stracefiles.append(file)

        for file in filter(lambda s: s not in stracefiles, files):
            if file != f"{usef}.pcapng":
                createdfiles.append(file)

        return stracefiles, createdfiles

    def _extract_files(self, output):
        temp1 = output.split(FILE_LIST_START)[1]
        temp2 = temp1.split(FILE_LIST_END)[0]

        files = temp2.strip().split("\n")

        for i, file in enumerate(files):
            files[i] = file.strip()

        return files

if __name__ == "__main__":
    from config import Config
    from arch import Arch
    import sys
    import os
    import traceback
    import logging

    qemulog = logging.getLogger("qemu")
    dynlog = logging.getLogger("dynamic")

    handler = logging.StreamHandler()
    qemulog.setLevel(logging.DEBUG)
    dynlog.setLevel(logging.DEBUG)
    qemulog.addHandler(handler)
    dynlog.addHandler(handler)

    conf = Config("../configs/iotsuite.conf")

    os.chdir("../test")

    dynamic = DynamicAnalyzer(conf)

    # startup the dynamic analyzer
    try:
        dynamic.startup()
        res = dynamic.run("testelf")
        logger.debug(f"{res}")
    except Exception as e:
        logger.error(f"{traceback.print_tb(sys.exc_info()[2])}\n{e}")
        dynamic.net.teardown(conf.GENERAL["SudoPasswd"])
        sys.exit(1)

    dynamic.shutdown()
