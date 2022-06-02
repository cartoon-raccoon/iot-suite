from enum import Enum

from .config import MAC_ADDR, NIC_HELPER

SUPPORTED_ARCHS = [
    "ARM",
    "MIPS",
    "Motorola 68000",
    "PowerPC",
    "x86",
    "x64",
]

class Arch(Enum):
    ARM = 1
    MIPS = 2
    MIPSEL = 3
    M68K = 4
    PPC = 5
    I386 = 6
    AMD64 = 7
    UNKW = 8

    def args(self, kern, vmdir):
        
        args = ARCH_ARGS[self]

        for i, arg in enumerate(args):
            args[i] = arg.format(vmdir, kern)
            
        return args

ARCH_CMDS = {
    Arch.ARM    : "qemu_system_arm",
    Arch.MIPS   : "qemu_system_mips",
    Arch.MIPSEL : "qemu_system_mipsel",
    Arch.M68K   : "qemu_system_m68k",
    Arch.PPC    : "qemu_system_ppc",
    Arch.I386   : "qemu_system_i386",
    Arch.AMD64  : "qemu_system_x86_64",
}

ARCH_ARGS = {
    Arch.ARM : [
        "-M", "versatilepb",
        "-kernel", "{}/{}",
        "-dtb", "{}/versatile-pb.dtb",
        "-append", "rootwait quiet root=/dev/sda console=ttyAMA0,115200",
        "-nic", "tap,model=rtl8139,helper={},mac={}".format(NIC_HELPER, MAC_ADDR)
    ]
}