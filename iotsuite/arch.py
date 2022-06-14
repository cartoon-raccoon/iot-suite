from enum import Enum

from config import CNC_MAC_ADDR, VM_MAC_ADDR, NIC_HELPER

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
    # adding cnc here as an option so it can be invoked the same way as
    # every other QEMU VM
    CNC = 8
    UNKW = 9

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
    Arch.CNC    : "qemu-system-x86_64",
}

ARCH_ARGS = {
    Arch.ARM : [
        "-M", "versatilepb",
        "-kernel", "{}/kernel.img",
        "-dtb", "{}/versatile-pb.dtb",
        "-drive", "file={}/rootfs.qcow2,if=scsi,format=qcow2",
        "-append", "rootwait quiet root=/dev/sda console=ttyAMA0,115200",
        "-nic", "tap,model=rtl8139,helper={},mac={}".format(NIC_HELPER, VM_MAC_ADDR)
    ],
    Arch.MIPS : [
        "-M", "malta", "-cpu", "mips32r6-generic",
        "-kernel", "{}/kernel.img",
        "-drive", "file={}/rootfs.qcow2,format=qcow2",
        "-append", "rootwait quiet root=/dev/sda",
        "-nic", "tap,model=pcnet,helper={},mac={}".format(NIC_HELPER, VM_MAC_ADDR)
    ],
    Arch.MIPSEL : [
        "-M", "malta", "-cpu", "mips32r6-generic",
        "-kernel", "{}/kernel.img",
        "-drive", "file={}/rootfs.qcow2,format=qcow2",
        "-append", "rootwait quiet root=/dev/sda",
        "-nic", "tap,model=pcnet,helper={},mac={}".format(NIC_HELPER, VM_MAC_ADDR)
    ],
    Arch.CNC : [
        "-drive", "file={}/rootfs.qcow2,format=qcow2",
        "-enable-kvm",
        "-nic", "tap,model=virtio-net-pci,helper={},mac={}".format(NIC_HELPER, CNC_MAC_ADDR),
        "-m", "2G", "-smp", "2",
    ],
}