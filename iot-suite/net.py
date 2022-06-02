import subprocess
from enum import Enum

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

    def __init__(self, chain: Chain, 
    target: str, target_args: list,
    dst_ip=None, src_ip = None,
    iface=None,
    protocol=None, dport=None, sport=None,
    table=Table.FILTER):
        self.table = table
        self.chain = chain
        self.target = target
        self.target_args = target_args
        self.dst_ip, self.src_ip = dst_ip, src_ip
        self.iface = iface
        self.protocol = protocol,
        self.dport, self.sport = dport, sport

    def insert(self):
        self._base_insert("-I")
    
    def append(self):
        self._base_insert("-A")

    def _base_insert(self, action):
        cmd = [
            "iptables", "-t", self.table.value(),
            action, self.chain.value()
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

        subprocess.run(cmd)

class Net:
    def __init__(self, bridge, ):
        pass

    