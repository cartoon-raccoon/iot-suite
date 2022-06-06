from enum import Enum

from config import MAC_ADDR, NIC_HELPER

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

    def args(self, vmdir):
        
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
}

ARCH_ARGS = {
    Arch.ARM : [
        "-M", "versatilepb",
        "-kernel", "{}/kernel.img",
        "-dtb", "{}/versatile-pb.dtb",
        "-drive", "file={}/rootfs.qcow2,if=scsi,format=qcow2",
        "-append", "rootwait quiet root=/dev/sda console=ttyAMA0,115200",
        "-nic", "tap,model=rtl8139,helper={},mac={}".format(NIC_HELPER, MAC_ADDR)
    ]
}