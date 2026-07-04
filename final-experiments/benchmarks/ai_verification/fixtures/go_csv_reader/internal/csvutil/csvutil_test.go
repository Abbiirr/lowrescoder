package csvutil_test

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/ai-verification/go-csv-reader/internal/csvutil"
)

func writeCSVTemp(t *testing.T, content string) string {
	t.Helper()
	f, err := os.CreateTemp(t.TempDir(), "test-*.csv")
	if err != nil {
		t.Fatal(err)
	}
	f.WriteString(content)
	f.Close()
	return f.Name()
}

func TestParseCSV(t *testing.T) {
	path := writeCSVTemp(t, "name,age\nalice,30\nbob,25\n")
	records, err := csvutil.ParseCSV(path)
	if err != nil {
		t.Fatal(err)
	}
	if len(records) != 3 {
		t.Fatalf("expected 3 rows, got %d", len(records))
	}
	if records[1][0] != "alice" {
		t.Fatalf("expected alice, got %q", records[1][0])
	}
}

func TestWriteCSV(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "out.csv")
	rows := [][]string{{"x", "y"}, {"1", "2"}, {"3", "4"}}
	if err := csvutil.WriteCSV(path, rows); err != nil {
		t.Fatal(err)
	}
	records, err := csvutil.ParseCSV(path)
	if err != nil {
		t.Fatal(err)
	}
	if len(records) != 3 {
		t.Fatalf("expected 3 rows, got %d", len(records))
	}
}

func TestCountRows(t *testing.T) {
	path := writeCSVTemp(t, "h1,h2\na,b\nc,d\ne,f\n")
	n, err := csvutil.CountRows(path)
	if err != nil {
		t.Fatal(err)
	}
	if n != 3 {
		t.Fatalf("expected 3 data rows, got %d", n)
	}
}

func TestFilterCSV(t *testing.T) {
	path := writeCSVTemp(t, "name,age\nalice,30\nbob,17\nchris,25\n")
	rows, err := csvutil.FilterCSV(path, func(row []string) bool {
		return row[1] != "17"
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(rows) != 3 {
		t.Fatalf("expected 3 rows (header+2), got %d", len(rows))
	}
	if rows[0][0] != "name" {
		t.Fatalf("expected header row, got %v", rows[0])
	}
}
