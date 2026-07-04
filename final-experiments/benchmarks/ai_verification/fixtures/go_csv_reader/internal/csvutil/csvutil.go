// Package csvutil provides CSV file reading and writing utilities.
// NOTE: uses deprecated io/ioutil — to be migrated to io and os packages.
package csvutil

import (
	"encoding/csv"
	"io/ioutil" //nolint:staticcheck
	"strings"
)

// ParseCSV reads a CSV file and returns all records.
func ParseCSV(path string) ([][]string, error) {
	data, err := ioutil.ReadFile(path) //nolint:staticcheck
	if err != nil {
		return nil, err
	}
	r := csv.NewReader(strings.NewReader(string(data)))
	return r.ReadAll()
}

// WriteCSV writes records to a CSV file, creating or overwriting it.
func WriteCSV(path string, rows [][]string) error {
	var sb strings.Builder
	w := csv.NewWriter(&sb)
	if err := w.WriteAll(rows); err != nil {
		return err
	}
	return ioutil.WriteFile(path, []byte(sb.String()), 0o644) //nolint:staticcheck
}

// CountRows returns the number of data rows (excluding header) in a CSV file.
func CountRows(path string) (int, error) {
	records, err := ParseCSV(path)
	if err != nil {
		return 0, err
	}
	if len(records) == 0 {
		return 0, nil
	}
	return len(records) - 1, nil
}

// FilterCSV reads a CSV file and returns rows where pred returns true.
// The header row (index 0) is always included in the output.
func FilterCSV(path string, pred func([]string) bool) ([][]string, error) {
	records, err := ParseCSV(path)
	if err != nil {
		return nil, err
	}
	if len(records) == 0 {
		return records, nil
	}
	result := [][]string{records[0]}
	for _, row := range records[1:] {
		if pred(row) {
			result = append(result, row)
		}
	}
	return result, nil
}
