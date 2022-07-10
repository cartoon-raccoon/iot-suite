from configparser import ConfigParser
import logging

from arch import Arch

logger = logging.getLogger("config")

# Config sections
GENERAL = "GENERAL"
STATIC = "STATIC"
HEURISTICS = "HEURISTICS"
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
_REQUIRED = [GENERAL, STATIC, HEURISTICS, CNC, SANDBOX, NETWORK]

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

class InvalidConfig(Exception):
    """
    Exception raised when a Config is invalid.
    """
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return f"InvalidConfig('{self.msg}')"

    def __str__(self):
        return self.msg

class Section:
    """
    Wraps a `ConfigParser` section proxy to provide access to config sections.

    A `Section` represents a section in the configuration file, such as
    `GENERAL` or `NETWORK`, and is automatically created when a configuration
    file is parsed. A `Section` should not be directly created; instead, it
    should be accessed from the main `Config` class as an attribute.
    
    The `__getitem__` method has been overloaded to return the value of 
    the associated configuration key when a `Section` instance is subscripted.

    # Example

    ```python
    conf = Config("/path/to/config/file.conf")

    # access the 'Username' key through a subscript
    user = conf.SANDBOX["Username"]
    ```

    All returned attributes will be strings; no integer parsing is performed.
    """
    def __init__(self, section, _ty, _global=None):
        self._section = section
        # type of section
        self._ty = _ty
        # global config settings for VMs
        self._global = _global

    def __getitem__(self, item):
        """
        Returns the value of the `item` key in the section.
        Returns `NoneType` if the key does not exist.

        `item` should normally be a string, but this method will
        accept any type accepted by `ConfigParser`'s `__getitem__`
        implementation.
        """
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
        return self.check_enabled("SSH")

    def qmp(self):
        """
        Convenience method to check whether a Section has QMP enabled.
        """
        return self.check_enabled("QMP")

    def check_enabled(self, maybe):
        """
        Convenience method to check whether a Section has a particular key enabled.
        """
        maybe = self[maybe]

        return maybe is not None \
        and (maybe.lower() == "yes" or maybe.lower() == "true")

class Config:
    """
    A class representing the global configuration for IotSuite.

    This class wraps a `ConfigParser` that is used to directly parse
    the configuration file, and adds additional logic and method
    overloading to present an API that most suits the use case of
    IoTSuite.

    At initialization, the configuration file is validated and parsed
    into the following main sections:

    - `GENERAL`, containing general uncategorized settings;
    - `STATIC`, containing settings for static analysis;
    - `HEURISTICS`, containing settings for analysis of the collected data;
    - `CNC`, containing configuration settings for the fake
    C2 VM;
    - `SANDBOX`, containing general configuration settings for the
    sandbox VM;
    - `NETWORK`, containing configuration settings for the network
    environment constructed for the VMs to interact, as well as
    configuration settings for the custom file transfer protocol
    used by IoTSuite.

    Each architecture supported by IoTSuite also has its own section,
    but these sections are not compulsory. The main purpose of these
    sections is to allow the user to define specific configurations for
    a specific architecture. All configuration settings accepted in
    `SANDBOX` will be overidden by the ones in these sections.

    For details on the API, see the methods.
    """

    def __init__(self, file):
        """
        Create a new instance of `Config` with a provided file path.
        """
        self.cp = ConfigParser()
        self.cp.read(file)

        self.parse_config()

    def __getitem__(self, item):
        """
        This method is bad code and should not be used. It will either
        be fixed or removed in the future.
        """
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
                raise InvalidConfig("settings for required arch not present in config")

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
            logger.error("attribute error when creating sandbox config")
            logger.error("this is a bug. please contact the developer.")
            raise e

    def iptables(self):
        #todo: parse iptables and return a list of IptablesRule
        return []
    
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
        """
        This method is called automatically on initialization. It validates
        the configuration and wraps `ConfigParser` functionality to create
        the API for `Config`. If any required sections do not exist,
        this method will raise an `InvalidConfig` exception.

        This method creates six main attributes: `GENERAL`, `STATIC`, `CNC`, 
        `HEURISTICS`, `SANDBOX`, and `NETWORK`, and a similar attribute for 
        every architecture-specific section defined in the config file. 
        These attributes can be accessed like any other attribute.

        # Example

        ```python
        # to get the sandbox section
        # parse_config is called automatically to validate and construct the config
        conf = Config("/path/to/config/file.conf")

        sandbox = conf.SANDBOX
        ```

        This yields a `Section` instance that can be subscripted to retrieve
        an arbitrary configuration key. See `Section` for more details.
        """

        #todo: check for iptables (not required but add section for it if exists)

        result = self._validate_config()

        if result is not None:
            raise InvalidConfig(f"invalid configuration: missing required section '{result}'")

        setattr(self, GENERAL, Section(self.cp[GENERAL], GENERAL))
        setattr(self, STATIC, Section(self.cp[STATIC], STATIC))
        setattr(self, HEURISTICS, Section(self.cp[HEURISTICS], HEURISTICS))
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
    def _validate_config(self):
        for section in _REQUIRED:
            try:
                _ = self.cp[section]
            except KeyError:
                return section
        
        return None