package dynamic

import (
	"errors"
	"fmt"
	"os/exec"
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
	// Public
	Config *QemuConfig
	//Private
	cmd     []string
	prompt  string
	process *exec.Cmd
	expect  *expect.Console
	started bool
}

type QemuConfig struct {
	// The architecture of the machine
	Arch int
	// The user to log in as, and password
	User   string
	Passwd string
	// The MAC address of the device
	Mac string
	// The fully qualified path to the tap device helper
	Helper string
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

	qcmdargs, err := ArchArgs(q.Config.Arch,
		"kernel.img",
		q.Config.Image,
		q.Config.Helper,
		q.Config.Mac,
	)
	if err != nil {
		return err
	}

	q.cmd = append(q.cmd, qcmdargs...)

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
	s = strings.Replace(s, prompt, "", 1)
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
		q.started = false
		return nil
	}
}
