from enum import Enum
import invoke
import logging

from config import NetConfig

logger = logging.getLogger("net")

SUDO_PASSWD = "03032001"
class Table(Enum):
    NAT = "nat"
    MANGLE = "mangle"
    FILTER = "filter"
    RAW = "raw"

class Chain(Enum):
    PREROUTING = "PREROUTING"
    POSTROUTING = "POSTROUTING"
    FORWARD = "FORWARD"
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"

class IptablesRule:
    """
    A class representing an `iptables` rule managed by IotSuite.
    """

    def __init__(self, chain: Chain, 
    target: str, target_args: list,
    dst_ip=None, src_ip = None,
    iface=None,
    protocol=None, dport=None, sport=None,
    table=Table.FILTER):
        """
        Constructs the `iptables` rule.

        Required arguments are:

        - `chain`
        - `target` - the action to take.
        - `target_args` - all arguments to add to the target.

        This should be a list

        Other optional arguments are:

        - `dst_ip` and `src_ip` - These should be strings.
        - `iface` - The network interface for `iptables` to listen on.
        - `protocol` - The protocol for `iptables` to filter by.
        - `dport` and `sport` - These should be integers.
        - `table` - The table to insert the `iptables` rule in. Like
        `iptables`, if no table is specified, this defaults to `FILTER`.
        """
        self.table = table
        self.chain = chain
        self.target = target
        self.target_args = target_args
        self.dst_ip, self.src_ip = dst_ip, src_ip
        self.iface = iface
        self.protocol = protocol
        self.dport, self.sport = dport, sport

    def __str__(self):
        """
        Constructs the rule with the append action (`-A`).
        """
        return ' '.join(self._construct_cmd("-A"))

    def insert(self):
        """
        Runs `iptables` to insert the rule (using option `-I`).
        """
        self._base_insert("-I")
    
    def append(self):
        """
        Runs `iptables` to append the rule (using option `-A`).
        """
        self._base_insert("-A")

    def _base_insert(self, action):
        cmd = self._construct_cmd(action)

        invoke.sudo(' '.join(cmd))

    def _construct_cmd(self, action):
        cmd = [
            "iptables", "-t", self.table.value,
            action, self.chain.value
        ]

        if self.iface is not None:
            cmd.extend(["-i", self.iface])
        
        if self.protocol is not None:
            cmd.extend(["-p", self.protocol])

        if self.dport is not None:
            cmd.extend(["--dport", str(self.dport)])

        if self.sport is not None:
            cmd.extend(["--sport", str(self.sport)])

        if self.dst_ip is None and self.src_ip is None:
            #todo: raise error
            pass

        if self.dst_ip is not None:
            cmd.extend(["-d", self.dst_ip])
        
        if self.src_ip is not None:
            cmd.extend(["-s", self.src_ip])

        cmd.extend(["-j", self.target])
        cmd.extend(self.target_args)

        return cmd

class Net:
    """
    Represents the network environment required to run the sandbox,
    allowing communication with the fake C2 server and the sandbox VM.

    It sets up the network environment, such as installing the bridge device,
    manages the DHCP server and its configuration, as well as injecting and
    flushing `iptables` rules.
    """
    def __init__(self, config: NetConfig):
        """
        Accepts a `NetConfig` to set up the network infrastructure.
        """
        self.bridge = config.br
        self.dhcpconf = config.dhcp
        self.ipaddr = config.ipaddr
        self.iptables = []

    def setup(self, sudo_passwd):
        logger.debug(f"adding bridge {self.bridge}")
        invoke.sudo(f"ip link add {self.bridge} type bridge", password=sudo_passwd)
        
        logger.debug(f"setting up bridge {self.bridge}")
        invoke.sudo(f"ip link set {self.bridge} up", password=sudo_passwd)

        logger.debug(f"adding IP address to bridge {self.bridge}")
        invoke.sudo(f"ip addr add {self.ipaddr}/24 brd + dev {self.bridge}", password=sudo_passwd)

        logger.debug(f"starting dhcpd with configuration file {self.dhcpconf}")
        invoke.sudo(f"dhcpd -cf {self.dhcpconf}", password=sudo_passwd, hide=True)

    def teardown(self, sudo_passwd):
        # flush iptables
        # kill dhcpd
        # remove bridge interface
        logger.debug("tearing down net")
        invoke.sudo("pkill dhcpd", password=sudo_passwd)

        logger.debug("dhcpd killed, deleting devices")
        invoke.sudo(f"ip link set {self.bridge} down", password=sudo_passwd)
        invoke.sudo(f"ip link delete {self.bridge} type bridge", password=sudo_passwd)

    def generate_dhcpconf(self):
        """
        Generates a `dhcpd` configuration file from the IoTSuite config.
        """
        pass

    def insert_iptables(self, rule):
        rule.insert()
        self.iptables.append(rule)

    def append_iptables(self, rule):
        rule.append()
        self.iptables.append(rule)

    def flush_iptables(table: Table, sudo_passwd):
        invoke.sudo(f"iptables -t {table.value} -F", password=sudo_passwd)

if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    logger.addHandler(handler)

    net = Net("br0", "../configs/dhcpd.conf", "192.168.0.1")
    net.setup(SUDO_PASSWD)
    net.teardown(SUDO_PASSWD)