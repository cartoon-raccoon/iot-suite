package orchestrator

import (
	"errors"
	"fmt"
	"os/exec"

	"github.com/cartoon-raccoon/iot-suite/dynamic"
)

type Orchestrator struct {
}

// CheckPathExes checks that all required executables are present
func CheckPathExes() error {
	required := []string{
		dynamic.QEMU_ARM_CMD,
		dynamic.QEMU_MIPS_CMD,
		dynamic.QEMU_MIPSEL_CMD,
		dynamic.QEMU_M68K_CMD,
		dynamic.QEMU_PPC_CMD,
		dynamic.QEMU_I386_CMD,
		dynamic.QEMU_AMD64_CMD,
		"strings", "ssdeep",
	}

	for _, elem := range required {
		_, err := exec.LookPath(elem)
		if err != nil {
			return errors.New(fmt.Sprintf("%s not in $PATH", elem))
		}
	}

	return nil
}
