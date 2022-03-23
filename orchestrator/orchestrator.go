package orchestrator

import (
	"errors"
	"fmt"
	"os/exec"
)

type Orchestrator struct {
}

// CheckPathExes checks that all required executables are present
func CheckPathExes() error {
	required := []string{
		QEMU_ARM_CMD, QEMU_MIPS_CMD,
		QEMU_MIPSEL_CMD, QEMU_M68K_CMD,
		QEMU_PPC_CMD, QEMU_I386_CMD,
		QEMU_AMD64_CMD, STRINGS_CMD,
		SSDEEP_CMD,
	}

	for _, elem := range required {
		_, err := exec.LookPath(elem)
		if err != nil {
			return errors.New(fmt.Sprintf("%s not in $PATH", elem))
		}
	}

	return nil
}

const (
	QEMU_ARM_CMD    = "qemu-system-arm"
	QEMU_MIPS_CMD   = "qemu-system-mips"
	QEMU_MIPSEL_CMD = "qemu-system-mipsel"
	QEMU_M68K_CMD   = "qemu-system-m68k"
	QEMU_PPC_CMD    = "qemu-system-ppc"
	QEMU_I386_CMD   = "qemu-system-i386"
	QEMU_AMD64_CMD  = "qemu-system-x86_64"
	STRINGS_CMD     = "strings"
	SSDEEP_CMD      = "ssdeep"
)
