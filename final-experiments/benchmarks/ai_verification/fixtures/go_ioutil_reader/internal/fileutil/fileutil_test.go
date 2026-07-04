package fileutil_test

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/ai-verification/go-ioutil-reader/internal/fileutil"
)

func writeTemp(t *testing.T, content string) string {
	t.Helper()
	f, err := os.CreateTemp(t.TempDir(), "test-*.txt")
	if err != nil {
		t.Fatal(err)
	}
	f.WriteString(content)
	f.Close()
	return f.Name()
}

func TestReadBytes(t *testing.T) {
	path := writeTemp(t, "hello world")
	data, err := fileutil.ReadBytes(path)
	if err != nil {
		t.Fatal(err)
	}
	if string(data) != "hello world" {
		t.Fatalf("unexpected content: %q", data)
	}
}

func TestWriteBytes(t *testing.T) {
	path := filepath.Join(t.TempDir(), "out.txt")
	if err := fileutil.WriteBytes(path, []byte("written")); err != nil {
		t.Fatal(err)
	}
	data, _ := os.ReadFile(path)
	if string(data) != "written" {
		t.Fatalf("unexpected: %q", data)
	}
}

func TestReadLines(t *testing.T) {
	path := writeTemp(t, "line1\nline2\nline3")
	lines, err := fileutil.ReadLines(path)
	if err != nil {
		t.Fatal(err)
	}
	if len(lines) != 3 {
		t.Fatalf("expected 3 lines, got %d: %v", len(lines), lines)
	}
}
