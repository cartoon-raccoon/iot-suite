from configparser import ConfigParser
import logging

logger = logging.getLogger("config")

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
    def __init__(self, section, _ty, _global=None):
        self._section = section
        # type of section
        self._ty = _ty
        # global config settings for VMs
        self._global = _global

    def __getitem__(self, item):
        # try to return the requested item
        try:
            return self._section[item]
        except KeyError:
            # if we can't find anything, check the global settings
            if self._global is not None:
                try:
                    return self._global[item]
                except KeyError:
                    # nothing even in global settings, return None
                    return None
            else:
                # global settings don't exist for this section,
                # return None
                return None

    def item(self, item):
        return self[item]

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

    @property
    def network(self):
        try:
            return Section(self.NETWORK, NETWORK)
        except AttributeError:
            return None
    
    @property
    def cnc(self):
        try:
            return Section(self.CNC, CNC)
        except AttributeError:
            return None

    @property
    def sandbox(self):
        try:
            return Section(self.SANDBOX, SANDBOX)
        except AttributeError:
            return None
    
    def arch(self, arch):
        try:
            return Section(self.cp[arch], arch, self.SANDBOX)
        except KeyError:
            return None

    def parse_config(self):

        if not self._validate_config():
            # todo: raise error
            logger.error("error: invalid config")
            return

        setattr(self, CNC, Section(self.cp[CNC], CNC))
        setattr(self, SANDBOX, Section(self.cp[SANDBOX], SANDBOX))
        setattr(self, NETWORK, Section(self.cp[NETWORK], NETWORK))

        for arch in _ARCHS:
            try:
                setattr(self, arch, Section(self.cp[arch], arch, self.SANDBOX))
            except KeyError:
                setattr(self, arch, None)
                continue

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