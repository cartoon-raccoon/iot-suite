package dynamic

import "os/exec"

type Qemu struct {
	Config  *QemuConfig
	cmd     []string
	process exec.Cmd
}

type QemuConfig struct {
	// host/port mapping
	PortFwds map[int16]int16
	// The architecture of the machine
	Arch int
	// The user to log in as, and password
	User   string
	Passwd string
	// The path to the kernel image
	Kernel string
	// The path to the disk image
	Drive string
}

// Constructs a completely empty Qemu instance
func NewQemu() *Qemu {
	return &Qemu{}
}

// Constructs a new instance of Qemu with a provided config
func NewQemuWithConfig(config *QemuConfig) *Qemu {
	return &Qemu{Config: config}
}

// Start Qemu as an interactive session with the user
func (q *Qemu) Interactive() {
	// construct the actual command to run
	// execute it and setup the pipes

	// do some goroutine magic here to read and write at the same time
}

// Start Qemu as a non-interactive session with the user
func (q *Qemu) NonInteractive() {

}

func (q *Qemu) SendCmd() {

}

// Stops the QEMU process
func (q *Qemu) Stop() {

}
