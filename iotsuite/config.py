from configparser import ConfigParser

# Config sections
CNC = "CNC"
SANDBOX = "SANDBOX"
ARM = "ARM"
MIPS = "MIPS"
MIPSEL = "MIPSEL"
M68K = "M68K"
I386 = "I386"
AMD64 = "AMD64"
NETWORK = "NETWORK"
IPTABLES = "IPTABLES"

_ARCHS = [ARM, MIPS, MIPSEL, M68K, I386, AMD64]

class Section:
    """
    Wraps a ConfigParser section proxy to provide access to configs
    """
    def __init__(self, section):
        self._section = section

class Config:
    def __init__(self, file):
        self.cp = ConfigParser()
        self.cp.read(file)

        self.parse_config()

    def __getitem__(self, item):
        # todo:
        # for sandbox, if global scope is given but does not exist,
        # return None
        # if arch-specific is given but does not exist, but global
        # setting exists, return global
        # else, return None
        if item in _ARCHS:
            try:
                return self.cp[item]
            except KeyError:
                return None
            
        try:
            return self.cp[item]
        except KeyError:
            return None

    @property
    def vm_qmp_port(self):
        """
        Returns None if no global port is set.
        """
        try:
            return int(self[SANDBOX]["QMPPort"])
        except KeyError:
            return None

    @property
    def c2_qmp_port(self):
        try:
            return int(self[CNC]["QMPPort"])
        except KeyError:
            return None

    def parse_config(self):

        if not self._validate_config():
            # todo: raise error
            return

        return

    # check that all required sections are present
    # architecture-specific sections are optional
    # todo: check that all ports are valid integers
    def _validate_config(self):
        try:
            _ = self.cp[CNC]
            _ = self.cp[SANDBOX]
            _ = self.cp[NETWORK]

            return True
        except KeyError:
            return False