// Package fileutil wraps common file I/O operations.
// NOTE: uses deprecated io/ioutil — to be migrated to io and os packages.
package fileutil

import (
	"io/ioutil" //nolint:staticcheck
	"strings"
)

// ReadBytes returns the full contents of path as a byte slice.
func ReadBytes(path string) ([]byte, error) {
	return ioutil.ReadFile(path) //nolint:staticcheck
}

// WriteBytes writes data to path, creating or truncating the file.
func WriteBytes(path string, data []byte) error {
	return ioutil.WriteFile(path, data, 0o644) //nolint:staticcheck
}

// ReadLines returns the file at path split into lines.
func ReadLines(path string) ([]string, error) {
	data, err := ioutil.ReadFile(path) //nolint:staticcheck
	if err != nil {
		return nil, err
	}
	raw := strings.Split(string(data), "\n")
	lines := make([]string, 0, len(raw))
	for _, l := range raw {
		if l != "" {
			lines = append(lines, l)
		}
	}
	return lines, nil
}
