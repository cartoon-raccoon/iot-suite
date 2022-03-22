package static

import (
	"bytes"
	"errors"
	"fmt"
	"os/exec"
	"strconv"
	"strings"
)

// StringOffset holds the value of a string found by `strings` and its offset in the file.
type StringOffset struct {
	Str    string
	Offset int64
}

// Strings represents an operation with `strings`
type Strings struct {
	Output []StringOffset
	cmd    *exec.Cmd
	raw    string
}

// NewStrings constructs a new `strings` operation
func NewStrings() (*Strings, error) {
	_, err := exec.LookPath("strings")
	if err != nil {
		return nil, errors.New("'strings' not in $PATH")
	}

	return &Strings{
		cmd: exec.Command("strings", "-t", "x"),
	}, nil
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

	ret := []StringOffset{}

	for _, element := range split {
		element = strings.TrimSpace(element)
		offstr := strings.Split(element, " ")
		if len(offstr) != 2 {
			fmt.Printf("received offset_str of length %d", len(offstr))
		}
		offset, err := strconv.ParseInt(offstr[0], 16, 64)
		if err != nil {
			return
		}
		ret = append(ret, StringOffset{Str: offstr[1], Offset: offset})
	}

	str.Output = ret
}
