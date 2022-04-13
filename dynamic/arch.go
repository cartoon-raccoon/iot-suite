package dynamic

import (
	"errors"
	"fmt"
)

const (
	// ARM architecture
	ARCH_ARM = iota
	// MIPS architecture
	ARCH_MIPS
	// MIPSEL architecture
	ARCH_MIPSEL
	// Motorola 68K architecture
	ARCH_M68K
	// PowerPC Architecture
	ARCH_PPC
	// Intel i386 architecture
	ARCH_I386
	// AMD64 architecture
	ARCH_AMD64
	// Architecture unknown/not yet known
	ARCH_UNK
)

// commands to use for invoking qemu
const (
	QEMU_ARM_CMD    = "qemu-system-arm"
	QEMU_MIPS_CMD   = "qemu-system-mips"
	QEMU_MIPSEL_CMD = "qemu-system-mipsel"
	QEMU_M68K_CMD   = "qemu-system-m68k"
	QEMU_PPC_CMD    = "qemu-system-ppc"
	QEMU_I386_CMD   = "qemu-system-i386"
	QEMU_AMD64_CMD  = "qemu-system-x86_64"
)

func ArchArgs(arch int, kern string, vmdir string, nic_helper string, mac string) ([]string, error) {
	args := make([]string, 0)
	switch arch {
	case ARCH_ARM:
		return append(args,
			"-M", "versatilepb",
			"-kernel", fmt.Sprintf("%s/%s", vmdir, kern),
			"-dtb", fmt.Sprintf("%s/versatile-pb.dtb", vmdir),
			"-drive", fmt.Sprintf("file=%s/rootfs.ext2,if=scsi,format=raw", vmdir),
			"-append", "rootwait quiet root=/dev/sda console=ttyAMA0,115200",
			"-nic", fmt.Sprintf("tap,model=rtl8139,helper=%s,mac=%s", nic_helper, mac),
		), nil
	case ARCH_MIPS:
		return append(args,
			"-M", "malta",
			"-cpu", "mips32r6-generic",
			"-kernel", fmt.Sprintf("%s/%s", vmdir, kern),
			"-drive", fmt.Sprintf("file=%s/rootfs.ext2,if=scsi,format=raw", vmdir),
			"-append", "rootwait root=/dev/sda quiet",
			"-nic", fmt.Sprintf("tap,model=pcnet,helper=%s,mac=%s", nic_helper, mac),
		), nil
	case ARCH_MIPSEL:
		return append(args,
			"-M", "malta",
			"-cpu", "mips32r6-generic",
			"-kernel", fmt.Sprintf("%s/%s", vmdir, kern),
			"-drive", fmt.Sprintf("file=%s/rootfs.ext2,if=scsi,format=raw", vmdir),
			"-append", "rootwait root=/dev/sda quiet",
			"-nic", fmt.Sprintf("tap,model=pcnet,helper=%s,mac=%s", nic_helper, mac),
		), nil
	case ARCH_M68K:
		return args, errors.New("m68k unimplemented")
	case ARCH_PPC:
		return args, errors.New("powerpc unimplemented")
	case ARCH_I386:
		return args, errors.New("i386 unimplemented")
	case ARCH_AMD64:
		return args, errors.New("amd64 unimplemented")
	default:
		return args, errors.New("unknown architecture")
	}
}

// Retrieves the qemu command for the architecture being used.
func ArchToCmd(arch int) (string, error) {
	switch arch {
	case ARCH_ARM:
		return QEMU_ARM_CMD, nil
	case ARCH_MIPS:
		return QEMU_MIPS_CMD, nil
	case ARCH_MIPSEL:
		return QEMU_MIPSEL_CMD, nil
	case ARCH_M68K:
		return QEMU_M68K_CMD, nil
	case ARCH_PPC:
		return QEMU_PPC_CMD, nil
	case ARCH_I386:
		return QEMU_I386_CMD, nil
	case ARCH_AMD64:
		return QEMU_AMD64_CMD, nil
	default:
		return "", errors.New("unknown architecture")
	}
}
