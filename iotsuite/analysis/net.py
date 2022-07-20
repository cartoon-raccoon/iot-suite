import dpkt
import dpkt.ethernet as eth
import re
import logging

logger = logging.getLogger("analysis-net")

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
            packets.append((ts, eth.Ethernet(buf)))

        return packets

    def collate_ips(self):
        # todo
        pass

    def _parse_dns_output(self, dns):
        res = self.dns_re.findall(dns)

        return res


