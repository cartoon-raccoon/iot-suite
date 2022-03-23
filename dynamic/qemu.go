package dynamic

import (
	"errors"
	"fmt"
	"os/exec"
	"path/filepath"
	"strings"

	expect "github.com/Netflix/go-expect"
)

type Qemu struct {
	Config  *QemuConfig
	cmd     []string
	process *exec.Cmd
	expect  *expect.Console
	started bool
}

type QemuConfig struct {
	// host/guest port mapping
	PortFwds map[int16]int16
	// The architecture of the machine
	Arch int
	// The user to log in as, and password
	User   string
	Passwd string
	// Arguments to pass to the kernel
	Append string
	// The path to the VM directory
	Image string
}

// Constructs a completely empty Qemu instance
func NewQemu() *Qemu {
	return &Qemu{started: false}
}

// Constructs a new instance of Qemu with a provided config
func NewQemuWithConfig(config *QemuConfig) *Qemu {
	return &Qemu{Config: config, started: false}
}

// Start Qemu as an interactive session with the user
func (q *Qemu) Interactive() {
	// construct the actual command to run
	// execute it and setup the pipes
	q.startup(true)
	// do some goroutine magic here to read and write at the same time
}

// Start Qemu as a non-interactive session with the user
func (q *Qemu) NonInteractive() {
	q.startup(false)
}

// Does the startup operations that are common between both modes
func (q *Qemu) startup(interactive bool) error {
	// convert the config into a qemu command
	err := q.constructQemuCmd()
	if err != nil {
		return err
	}
	// create the qemu command with its args
	q.process = exec.Command(q.cmd[0])
	q.process.Args = q.cmd[1:]

	// create a new console
	pexpect, err := expect.NewConsole()
	if err != nil {
		return err
	}
	q.expect = pexpect

	err = q.process.Start()
	if err != nil {
		return err
	}

	if interactive {
		//todo: print startup sequence
	}

	q.started = true

	return nil
}

// Constructs the QEMU command
func (q *Qemu) constructQemuCmd() error {
	maincmd, err := ArchToCmd(q.Config.Arch)
	if err != nil {
		return err
	}

	q.cmd = append(q.cmd, maincmd)
	vmpath, err := filepath.Abs(q.Config.Image)
	if err != nil {
		return err
	}

	// get the machine name and append it to the command
	machine, err := ArchToMachine(q.Config.Arch)
	if err != nil {
		return err
	}
	q.cmd = append(q.cmd, "-M", machine)

	// get the kernel path and append it to the command
	kernelpath := fmt.Sprintf("%s/zImage", vmpath)
	q.cmd = append(q.cmd, "-kernel", kernelpath)

	// get the DTB path and append it to the command
	dtb, err := ArchToDTB(q.Config.Arch)
	if err != nil {
		return err
	}
	dtbpath := fmt.Sprintf("%s/%s.dtb", vmpath, dtb)
	q.cmd = append(q.cmd, "-dtb", dtbpath)

	//get drive path and append it to the command
	drivepath := fmt.Sprintf("%s/rootfs.ext2,if=scsi,format=raw", vmpath)
	q.cmd = append(q.cmd, "-drive", drivepath)

	//get kernel args and append it to the command
	q.cmd = append(q.cmd, "-append", q.Config.Append)

	q.cmd = append(q.cmd, "-net", "nic,model=rtl8139")
	//get hostfwds and append it to the command
	var hostfwdstrs []string
	for k, v := range q.Config.PortFwds {
		hostfwdstrs = append(hostfwdstrs,
			fmt.Sprintf("hostfwd=tcp::%d-:%d", k, v),
		)
	}
	hostfwds := fmt.Sprintf("user,id=net0,%s", strings.Join(hostfwdstrs, ","))
	q.cmd = append(q.cmd, "-net", hostfwds)

	q.cmd = append(q.cmd, "-nographic", "-serial", "stdio", "-mon", "pipe:/tmp/guest")

	return nil
}

// todo
// Runs a command on the VM
func (q *Qemu) RunCmd() (string, error) {
	if !q.started {
		return "", errors.New("QEMU not yet started")
	}
	return "", nil
}

// Stops the QEMU process
func (q *Qemu) Stop() {

}
