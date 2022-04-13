package main

import (
	"fmt"
	"os"
	"strings"

	"github.com/cartoon-raccoon/iot-suite/dynamic"
	"github.com/cartoon-raccoon/iot-suite/orchestrator"
	"github.com/cartoon-raccoon/iot-suite/static"
)

func main() {
	testQemu()
}

func testQemu() {
	conf := dynamic.QemuConfig{
		Arch:   dynamic.ARCH_ARM,
		User:   "tester",
		Passwd: "itestmalware",
		Mac:    "52:54:01:12:34:56",
		Helper: "/usr/lib/qemu/qemu-bridge-helper",
		Image:  "vms/arm",
	}
	qemu := dynamic.NewQemuWithConfig(&conf)
	err := qemu.NonInteractive()
	if err != nil {
		qemu.Stop()
		panic(err)
	}
	res, err := qemu.RunCmd("echo \"Hello\"")
	fmt.Printf("Result: %v\n", res)
	if err != nil {
		qemu.Stop()
		panic(err)
	}
	qemu.Stop()
}

func testStatic() {
	file := os.Args[1]

	err := orchestrator.CheckPathExes()
	if err != nil {
		fmt.Fprintf(os.Stderr, "%s\n", err)
	}

	sa, err := static.NewWith(file)
	if err != nil {
		fmt.Fprintf(os.Stderr, "%s\n", err)
	}

	strs, err := sa.RunStrings()
	if err != nil {
		fmt.Fprintf(os.Stderr, "%s\n", err)
	}

	for _, elem := range strs {
		fmt.Printf("0x%x %s\n", elem.Offset, elem.Str)
	}

	sha256, err := sa.CalcSHA256()
	if err != nil {
		fmt.Fprintf(os.Stderr, "%s\n", err)
	}

	fmt.Printf("sha256: %s\n", bytearrayToString(sha256[:]))

	md5, err := sa.CalcMD5()
	if err != nil {
		fmt.Fprintf(os.Stderr, "%s\n", err)
	}

	fmt.Printf("md5: %s\n", bytearrayToString(md5[:]))
}

func bytearrayToString(b []byte) string {
	strs := []string{}
	for _, elem := range b {
		s := fmt.Sprintf("%02x", elem)
		strs = append(strs, s)
	}

	return strings.Join(strs, "")
}
