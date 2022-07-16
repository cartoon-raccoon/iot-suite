import dpkt
import dpkt.ethernet as eth
import re
import logging

logger = logging.getLogger("analysis-net")

class NetAnalyzer:

    DNS_REGEX = r">> *Matched Request - (.*)."

    def __init__(self, pcapfile, dns):
        self.pcap = dpkt.pcap.Reader(open(pcapfile, "rb"))
        self.dns_re = re.compile(self.DNS_REGEX)
        self.packets = []

        self._parse_dns_output(dns)

    def __getitem__(self, idx):
        return self.packets[idx]

    def __iter__(self):
        return self.packets

    def read_packets(self):
        # todo: once timing has been implemented in analyse.py,
        # make ts useful
        for ts, buf in self.pcap:
            self.packets.append((ts, eth.Ethernet(buf)))

    def collate_ips(self):
        # todo
        pass

    def _parse_dns_output(self, dns):
        res = self.dns_re.findall(dns)

        self.dns_domains = res


