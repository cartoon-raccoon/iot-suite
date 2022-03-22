package static

import (
	"bytes"
	"errors"
	"os/exec"
	"strconv"
	"strings"
)

// StringOffset holds the value of a string found by `strings` and its offset in the file.
type StringOffset struct {
	Offset int64
	Str    string
}

// Strings represents an operation with `strings`
type Strings struct {
	Output []StringOffset
	cmd    *exec.Cmd
	raw    string
}

// NewStrings constructs a new `strings` operation
func NewStrings() *Strings {
	return &Strings{
		cmd: exec.Command("strings", "-t", "x"),
	}
}

// Run runs `strings` on the given file
func (str *Strings) Run(filename string) error {
	if len(filename) <= 0 {
		return errors.New("empty filename given")
	}

	str.cmd.Args = append(str.cmd.Args, filename)

	output, err := str.cmd.Output()
	if err != nil {
		return errors.New("placeholder text: error running strings")
	}

	str.raw = bytes.NewBuffer(output).String()

	str.parseOutput()

	return nil
}

// Reset empties `str` and sets all fields to the zero value.
func (str *Strings) Reset() {
	str.raw = ""
	str.Output = []StringOffset{}
}

func (str *Strings) parseOutput() {
	split := strings.Split(str.raw, "\n")

	for _, element := range split {
		//fmt.Printf("%s\n", element)
		element = strings.TrimSpace(element)
		offstr := strings.Split(element, " ")
		offset, err := strconv.ParseInt(offstr[0], 16, 64)
		if err != nil {
			return
		}
		strs := strings.Join(offstr[1:], " ")
		str.Output = append(str.Output, StringOffset{Offset: offset, Str: strs})
	}
}
