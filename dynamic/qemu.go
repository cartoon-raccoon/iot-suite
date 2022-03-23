package dynamic

import (
	"errors"
	"fmt"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"

	expect "github.com/Netflix/go-expect"
)

const (
	USER_PROMPT = "$"
	ROOT_PROMPT = "#"
)

type Qemu struct {
	Config  *QemuConfig
	cmd     []string
	prompt  string
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
func (q *Qemu) Interactive() error {
	// construct the actual command to run
	// execute it and setup the pipes
	err := q.startup(true)
	if err != nil {
		return err
	}
	return nil
	// do some goroutine magic here to read and write at the same time
}

// Start Qemu as a non-interactive session with the user
func (q *Qemu) NonInteractive() error {
	err := q.startup(false)
	if err != nil {
		return err
	}
	return nil
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
	q.process.Args = q.cmd[0:]

	//! debug
	fmt.Printf("Running command %v\n", q.process)

	// create a new console
	pexpect, err := expect.NewConsole()
	if err != nil {
		return err
	}
	q.expect = pexpect
	// connect streams to Tty
	q.process.Stdin = q.expect.Tty()
	q.process.Stdout = q.expect.Tty()
	q.process.Stderr = q.expect.Tty()

	q.prompt = fmt.Sprintf("%s ", q.getPrompt())

	err = q.process.Start()
	if err != nil {
		return err
	}

	if interactive {
		q.Stop()
		panic("qemu.startup(true): unimplemented")
	} else {
		err = q.Login()
		if err != nil {
			return err
		}
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
	drivepath := fmt.Sprintf("file=%s/rootfs.ext2,if=scsi,format=raw", vmpath)
	q.cmd = append(q.cmd, "-drive", drivepath)

	//get kernel args and append it to the command
	q.cmd = append(q.cmd, "-append", q.Config.Append)

	q.cmd = append(q.cmd, "-net", "nic,model=rtl8139")
	//get hostfwds and append it to the command
	if len(q.Config.PortFwds) > 0 {
		var hostfwdstrs []string
		for k, v := range q.Config.PortFwds {
			hostfwdstrs = append(hostfwdstrs,
				fmt.Sprintf("hostfwd=tcp::%d-:%d", k, v),
			)
		}
		hostfwds := fmt.Sprintf("user,id=net0,%s", strings.Join(hostfwdstrs, ","))
		q.cmd = append(q.cmd, "-net", hostfwds)
	}

	q.cmd = append(
		q.cmd, "-nographic",
		"-serial", "stdio",
		"-chardev", "pipe,id=mon0,path=/tmp/guest",
		"-mon", "chardev=mon0,mode=control",
	)

	return nil
}

func (q *Qemu) Login() error {
	buf, err := q.expect.Expect(
		expect.String("iotsuite login: "),
		expect.WithTimeout(30*time.Second),
	)
	if err != nil {
		fmt.Printf("%s\n", err)
	}
	if !strings.HasSuffix(buf, "iotsuite login: ") {
		fmt.Printf("%s\n", buf)
		return err
	} else {
		//! debug
		fmt.Printf("Sending username\n")
		q.expect.SendLine(q.Config.User)
		buf, err = q.expect.Expect(
			expect.String("Password: "),
			expect.WithTimeout(30*time.Second),
		)
	}
	if !strings.HasSuffix(buf, "Password: ") {
		fmt.Printf("%s\n", buf)
		return err
	} else {
		//! debug
		fmt.Printf("Sending password\n")
		q.expect.SendLine(q.Config.Passwd)
		buf, err = q.expect.Expect(
			expect.String(q.prompt),
			expect.WithTimeout(30*time.Second),
		)
		if !strings.Contains(buf, q.prompt) ||
			strings.Contains(buf, "Login incorrect") {
			fmt.Printf("%s\n", buf)
			return errors.New("Unable to login")
		}
	}
	return nil
}

func (q *Qemu) setNonIntPrompt(prompt string) error {
	q.RunCmd(fmt.Sprintf("export PS1='%s'", prompt))
	_, err := q.expect.ExpectString(prompt)
	if err != nil {
		return err
	}
	q.prompt = prompt
	return nil
}

func (q *Qemu) getPrompt() string {
	if q.Config.User == "root" {
		return ROOT_PROMPT
	} else {
		return USER_PROMPT
	}
}

// Represents the result returned by a command
type CmdResult struct {
	Output   string
	Exitcode int
}

// todo
// Runs a command on the VM
func (q *Qemu) RunCmd(cmd string) (CmdResult, error) {
	if !q.started {
		return CmdResult{}, errors.New("QEMU not yet started")
	}
	// run the command
	q.expect.SendLine(cmd)
	// receive the output
	s, err := q.expect.ExpectString(q.prompt)
	if err != nil {
		return CmdResult{}, err
	}
	s = sanitize(s, q.prompt, cmd)

	//! debug
	fmt.Printf("Output: %s\n", s)
	// get the exit code
	q.expect.SendLine("echo $?")
	s2, err := q.expect.ExpectString(q.prompt)
	if err != nil {
		return CmdResult{}, err
	}

	s2 = sanitize(s2, q.prompt, "echo $?")

	//! debug
	fmt.Printf("Exitcode: %s\n", s2)
	code, err := strconv.Atoi(s2)
	if err != nil {
		return CmdResult{}, err
	}
	return CmdResult{
		Output:   s,
		Exitcode: code,
	}, nil
}

// Strips out the prompt, the command that was sent, and any
// leading or trailing whitespace
func sanitize(s string, prompt string, cmd string) string {
	s = strings.Replace(s, prompt, "", 1000)
	s = strings.Replace(s, cmd, "", 1000)
	s = strings.TrimSpace(s)

	return s
}

// Stops the QEMU process
func (q *Qemu) Stop() error {
	q.process.Process.Signal(syscall.SIGINT)
	_, err := q.process.Process.Wait()
	if err != nil {
		return err
	} else {
		return nil
	}
}
