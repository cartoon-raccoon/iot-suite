from configparser import ConfigParser
import logging

from arch import Arch

logger = logging.getLogger("config")

# Config sections
GENERAL = "GENERAL"
CNC = "CNC"
SANDBOX = "SANDBOX"
ARM = "ARM"
MIPS = "MIPS"
MIPSEL = "MIPSEL"
M68K = "M68K"
PPC = "POWERPC"
I386 = "I386"
AMD64 = "AMD64"
NETWORK = "NETWORK"
IPTABLES = "IPTABLES"

_ARCHS = [ARM, MIPS, MIPSEL, M68K, PPC, I386, AMD64]

class QemuConfig:
    """
    Class representing the configuration of a QEMU instance.
    """
    def __init__(self, arch: Arch, 
        user, passwd, image, helper, mac,
        login_prompt, qmp_port=None, qmp=False
    ):
        """
        The following arguments are required:

        - `arch` - The architecture of the instance.
        - `user` and `passwd` - The user to log in as and its password.
        - `image` - The directory containing the VM image files.
        - `helper` - The NIC helper to use for setting up the TAP devices.
        - `mac` - The MAC address to start the VM with.
        - `login_prompt` - The login prompt to expect for to send the password.
        
        The other two optional arguments concern QMP settings. These default to `None`
        and False respectively, as sandbox VMs should not make use of QMP.
        """
        self.arch = arch
        self.user = user
        self.passwd = passwd
        self.image = image
        self.nic_helper = helper
        self.macaddr = mac
        self.qmp_port = qmp_port
        self.login_prompt = login_prompt
        self.qmp = qmp

class NetConfig:
    """
    Class representing the configuration of a Net class.
    """
    def __init__(self, bridge, dhcpconf, ipaddr):
        """
        The three arguments to this function should all be strings.

        - `bridge` - The name of the bridge interface to use.
        - `dhcpconf` - The path to the dhpcd config file.
        - `ipaddr` - The IP address of the bridge interface.
        """
        self.br = bridge
        self.dhcp = dhcpconf
        self.ipaddr = ipaddr

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
            return self._section[item].strip('"')
        except KeyError:
            # if we can't find anything, check the global settings
            if self._global is not None:
                try:
                    return self._global[item].strip('"')
                except KeyError:
                    # nothing even in global settings, return None
                    return None
            else:
                # global settings don't exist for this section,
                # return None
                return None

    def item(self, item):
        """
        Convenience method for returning configuration items.
        """
        return self[item]

    def ssh(self):
        """
        Convenience method to check whether a Section has SSH enabled.
        """
        return self._eval_true_or_false(self["SSH"])

    def qmp(self):
        """
        Convenience method to check whether a Section has QMP enabled.
        """
        return self._eval_true_or_false(self["QMP"])

    def _eval_true_or_false(self, maybe):
        return maybe is not None and maybe == "yes"

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
        Gets the QMP port used by the sandbox VM.

        Returns None if no global port is set.
        """
        try:
            return int(self[SANDBOX]["QMPPort"])
        except KeyError:
            return None

    @property
    def c2_qmp_port(self):
        """
        Gets the QMP port used by the C2 VM.

        Returns None if no global port is set.
        """
        try:
            return int(self[CNC]["QMPPort"])
        except KeyError:
            return None

    @property
    def network(self):
        """
        Returns a complete `NetConfig` parsed from the config file.

        Returns None if the NETWORK section does not exist.
        """
        try:
            net = self.NETWORK
            
            return NetConfig(
                net["BridgeName"],
                net["DHCPConf"],
                net["IpAddr"]
            )
        except AttributeError:
            return None
    
    @property
    def cnc(self):
        """
        Returns a complete configuration for the CNC VM.
        """
        try:
            cnc = self.CNC
            net = self.NETWORK

            return QemuConfig(
                Arch.CNC,
                cnc["Username"],
                cnc["Password"],
                cnc["Image"],
                net["NicHelper"],
                cnc["MacAddr"],
                cnc["LoginPrompt"],
                qmp_port=int(cnc["QMPPort"]),qmp=cnc.qmp()
            )
        except AttributeError as e:
            raise e

    def sandbox(self, arch: Arch):
        """
        Constructs a `QemuConfig` based on the `Arch` passed to it with all
        the requisite attributes and fields set.
        """
        try:
            net = self.NETWORK
            arch_config = self.arch(arch.value)

            if arch_config is None:
                logger.error("error: settings for required arch not present in config")
                return None

            try:
                qmp_port = int(arch_config["QMPPort"])
            except TypeError:
                qmp_port = None

            return QemuConfig(
                arch,
                arch_config["Username"],
                arch_config["Password"],
                arch_config["Image"],
                net["NicHelper"],
                arch_config["MacAddr"],
                arch_config["LoginPrompt"],
                qmp_port=qmp_port, qmp=arch_config.qmp()
            )
        except AttributeError as e:
            raise e
    
    def arch(self, arch: str):
        """
        Returns the configuration settings for the architecture specified.
        The parameter has to be a string or the function will return None.

        Returns None if the configuration section does not exist.
        """
        try:
            return Section(self.cp[arch], arch, self.SANDBOX)
        except KeyError:
            return None

    def parse_config(self):

        if not self._validate_config():
            # todo: raise error
            logger.error("error: invalid config")
            return

        setattr(self, GENERAL, Section(self.cp[GENERAL], GENERAL))
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
            _ = self.cp[GENERAL]
            _ = self.cp[CNC]
            _ = self.cp[SANDBOX]
            _ = self.cp[NETWORK]

            return True
        except KeyError:
            return False