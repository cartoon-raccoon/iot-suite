package types

import "path"

// A Sample represents a malware sample to be tested.
type Sample struct {
	Name string
	Path string
}

// NewSample constructs a new Sample.
func NewSample(name string) *Sample {
	return &Sample{
		Name: name,
		Path: path.Base(name),
	}
}
