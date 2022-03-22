package types

import "path"

// A Sample represents a malware sample to be tested.
type Sample struct {
	Name string
	Path string
}

// NewSample constructs a new Sample.
func NewSample(filepath string) *Sample {
	return &Sample{
		Name: path.Base(filepath),
		Path: filepath,
	}
}
