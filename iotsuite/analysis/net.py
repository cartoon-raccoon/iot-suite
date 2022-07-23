import dpkt
import dpkt.ethernet as eth
import dpkt.ip as ip
import dpkt.ip6 as ip6
import re
import socket

from abc import ABC

import iotsuite.utils as utils

logger = utils.logger.getChild("analysis-net")

class Packet(ABC):
    """
    Abstract class for creating decoded packet instances.
    """
    def __init__(self, ts, src, dst, sport, dport, data):
        self.ts = ts
        self.src = src
        self.dst = dst
        self.sport = sport
        self.dport = dport
        self.data = data

class IP(Packet):
    pass

class IP6(Packet):
    pass

class NetResult:
    def __init__(self, packets, dns):
        self.packets = packets
        self.dns = dns

    def __getitem__(self, idx):
        return self.packets[idx]

    def __iter__(self):
        return self.packets

class NetAnalyzer:

    DNS_REGEX = r">> *Matched Request - (.*)."

    def __init__(self):
        self.pcap = None
        self.dns_re = re.compile(self.DNS_REGEX)

    def set_pcap_file(self, pcapfile):
        self.pcap = dpkt.pcap.Reader(open(pcapfile, "rb"))

    def get_result(self, dns):
        return NetResult(
            self.read_packets(),
            self._parse_dns_output(dns)
        )

    def reset(self):
        self.pcap = None

    def read_packets(self):
        packets = []
        # todo: once timing has been implemented in analyse.py,
        # make ts useful
        for ts, buf in self.pcap:
            packets.append((ts, eth.Ethernet(buf).data))

        return packets

    def collate_ips(self):
        # todo
        pass

    def _parse_packet_data(self, ts, packet):
        utils.todo()
        
        # todo: use python class magic to streamline this
        if isinstance(packet, ip.IP):
            return IP(ts,
                socket.inet_ntop(socket.AF_INET, packet.src),
                socket.inet_ntop(socket.AF_INET, packet.dst)
            )
        elif isinstance(packet, ip6.IP6):
            i = socket.AF_INET6
        else:
            utils.unreachable()

    def _parse_dns_output(self, dns):
        res = self.dns_re.findall(dns)

        return res


