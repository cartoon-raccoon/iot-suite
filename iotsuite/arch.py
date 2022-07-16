from enum import Enum

#* Names as defined in PyELFTools.
#! Changing these strings will break IoTSuite!
ARM = "ARM"
MIPS = "MIPS"
M68K = "Motorola 68000"
PPC = "PowerPC"
I386 = "x86"
AMD64 = "x64"

SUPPORTED_ARCHS = [
    ARM,
    MIPS, # MIPSEL is MIPS with little endian variant
    M68K,
    PPC,
    I386,
    AMD64,
]

def supports(arch):
    """
    Checks whether an architecture is supported.
    """
    return arch in SUPPORTED_ARCHS

class Arch(Enum):
    """
    An Enum with variants representing each architecture supported by
    IotSuite.
    """

    ARM = "ARM"
    MIPS = "MIPS"
    MIPSEL = "MIPSEL"
    M68K = "M68K"
    PPC = "PPC"
    I386 = "I386"
    AMD64 = "AMD64"
    # adding cnc here as an option so it can be invoked the same way as
    # every other QEMU VM
    CNC = "CNC"
    UNKW = 0

    def args(self, vmdir, helper, macaddr):
        """
        Returns the command line arguments for invoking QEMU for the architecture.
        """
        ARCH_ARGS = {
            Arch.ARM : [
                "-M", "versatilepb",
                "-kernel", "{}/kernel.img",
                "-dtb", "{}/versatile-pb.dtb",
                "-drive", "file={}/rootfs.qcow2,if=scsi,format=qcow2",
                "-append", "rootwait quiet root=/dev/sda console=ttyAMA0,115200",
                "-nic", f"tap,model=rtl8139,helper={helper},mac={macaddr}"
            ],
            Arch.MIPS : [
                "-M", "malta", "-cpu", "mips32r6-generic",
                "-kernel", "{}/kernel.img",
                "-drive", "file={}/rootfs.qcow2,format=qcow2",
                "-append", "rootwait quiet root=/dev/sda",
                "-nic", f"tap,model=pcnet,helper={helper},mac={macaddr}"
            ],
            Arch.MIPSEL : [
                "-M", "malta", "-cpu", "mips32r6-generic",
                "-kernel", "{}/kernel.img",
                "-drive", "file={}/rootfs.qcow2,format=qcow2",
                "-append", "rootwait quiet root=/dev/sda",
                "-nic", f"tap,model=pcnet,helper={helper},mac={macaddr}"
            ],
            Arch.CNC : [
                "-drive", "file={}/rootfs.qcow2,format=qcow2",
                "-enable-kvm",
                "-nic", f"tap,model=virtio-net-pci,helper={helper},mac={macaddr}",
                "-m", "2G", "-smp", "2",
            ],
        }        
        
        args = ARCH_ARGS[self]

        for i, arg in enumerate(args):
            args[i] = arg.format(vmdir)
            
        return args

ARCH_CMDS = {
    Arch.ARM    : "qemu-system-arm",
    Arch.MIPS   : "qemu-system-mips",
    Arch.MIPSEL : "qemu-system-mipsel",
    Arch.M68K   : "qemu-system-m68k",
    Arch.PPC    : "qemu-system-ppc",
    Arch.I386   : "qemu-system-i386",
    Arch.AMD64  : "qemu-system-x86_64",
    Arch.CNC    : "qemu-system-x86_64",
}