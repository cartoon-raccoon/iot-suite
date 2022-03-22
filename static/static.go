package static

import (
	"crypto/md5"
	"crypto/sha256"
	"os"
	"path/filepath"

	"github.com/cartoon-raccoon/iot-suite/types"
)

const (
	SHA256 int = iota
	SHA1
	MD5
)

// StaticAnalyzer represents the static analyzer of the program.
type StaticAnalyzer struct {
	sample  *types.Sample
	strings *Strings
}

// New returns an empty StaticAnalyzer.
func New() *StaticAnalyzer {
	return &StaticAnalyzer{strings: NewStrings()}
}

// NewWith
func NewWith(fpath string) (*StaticAnalyzer, error) {
	sa := New()
	err := sa.Set(fpath)

	if err != nil {
		return nil, err
	}

	return sa, nil
}

func (sa *StaticAnalyzer) Set(fpath string) error {
	fpath, err := filepath.Abs(fpath)
	if err != nil {
		return err
	}

	if _, err := os.Open(fpath); err != nil {
		return err
	}

	sa.sample, err = types.NewSample(fpath)

	if err != nil {
		return err
	}

	return nil
}

func (sa *StaticAnalyzer) RunStrings() ([]StringOffset, error) {
	err := sa.strings.Run(sa.sample.Path)
	if err != nil {
		return []StringOffset{}, err
	}

	strs := sa.strings.Output

	sa.strings.Reset()
	return strs, nil
}

func (sa *StaticAnalyzer) CalcSHA256() ([sha256.Size]byte, error) {
	if sa.sample.Data == nil {
		dat, err := os.ReadFile(sa.sample.Path)
		if err != nil {
			return [sha256.Size]byte{}, err
		}
		sa.sample.Data = dat
	}

	return sha256.Sum256(sa.sample.Data), nil
}

func (sa *StaticAnalyzer) CalcMD5() ([md5.Size]byte, error) {
	if sa.sample.Data == nil {
		dat, err := os.ReadFile(sa.sample.Path)
		if err != nil {
			return [md5.Size]byte{}, err
		}
		sa.sample.Data = dat
	}

	return md5.Sum(sa.sample.Data), nil
}
