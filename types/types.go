package types

import (
	"os"
	"path"
	"path/filepath"
)

// A Sample represents a malware sample to be tested.
type Sample struct {
	Name string
	Path string
	Data []byte
}

// NewSample constructs a new Sample.
func NewSample(fpath string) (*Sample, error) {
	abs, err := filepath.Abs(fpath)
	if err != nil {
		return nil, err
	}
	return &Sample{
		Name: path.Base(fpath),
		Path: abs,
	}, nil
}

// ReadIn reads the data from the file into an in-memory buffer.
func (sample *Sample) ReadIn() error {
	dat, err := os.ReadFile(sample.Path)

	if err != nil {
		return err
	}

	sample.Data = dat

	return nil
}
