package dynamic

import "errors"

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

// Retrieves the qemu machine name for the given arch
func ArchToMachine(arch int) (string, error) {
	switch arch {
	case ARCH_ARM:
		return "versatilepb", nil
	case ARCH_MIPS:
		return "malta", nil
	default:
		return "", errors.New("unknown architecture")
	}
}

func ArchToDTB(arch int) (string, error) {
	switch arch {
	case ARCH_ARM:
		return "versatile-pb", nil
	default:
		return "", errors.New("unknown architecture")
	}
}
