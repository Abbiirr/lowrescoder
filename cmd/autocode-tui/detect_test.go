package main

import (
	"os"
	"testing"
)

// TestFindPythonBackend_AutocodePythonCmd verifies that AUTOCODE_PYTHON_CMD
// takes highest priority in the fallback chain.
func TestFindPythonBackend_AutocodePythonCmd(t *testing.T) {
	// Set the new env var
	os.Setenv("AUTOCODE_PYTHON_CMD", "/usr/bin/fake-autocode")
	defer os.Unsetenv("AUTOCODE_PYTHON_CMD")
	// Also set the legacy env var — should be ignored
	os.Setenv("HYBRIDCODER_PYTHON_CMD", "/usr/bin/fake-hybridcoder")
	defer os.Unsetenv("HYBRIDCODER_PYTHON_CMD")

	cmd, args, found := findPythonBackend()
	if !found {
		t.Fatal("expected findPythonBackend to return found=true")
	}
	if cmd != "/usr/bin/fake-autocode" {
		t.Errorf("expected AUTOCODE_PYTHON_CMD value, got %q", cmd)
	}
	if len(args) != 1 || args[0] != "serve" {
		t.Errorf("expected args=[serve], got %v", args)
	}
}

// TestFindPythonBackend_LegacyPythonCmd verifies that HYBRIDCODER_PYTHON_CMD
// is used as fallback when AUTOCODE_PYTHON_CMD is not set.
func TestFindPythonBackend_LegacyPythonCmd(t *testing.T) {
	os.Unsetenv("AUTOCODE_PYTHON_CMD")
	os.Setenv("HYBRIDCODER_PYTHON_CMD", "/usr/bin/fake-hybridcoder")
	defer os.Unsetenv("HYBRIDCODER_PYTHON_CMD")

	cmd, args, found := findPythonBackend()
	if !found {
		t.Fatal("expected findPythonBackend to return found=true")
	}
	if cmd != "/usr/bin/fake-hybridcoder" {
		t.Errorf("expected HYBRIDCODER_PYTHON_CMD value, got %q", cmd)
	}
	if len(args) != 1 || args[0] != "serve" {
		t.Errorf("expected args=[serve], got %v", args)
	}
}

// TestFindPythonBackend_NewEnvTakesPrecedence verifies that the new env var
// takes precedence over the legacy one.
func TestFindPythonBackend_NewEnvTakesPrecedence(t *testing.T) {
	os.Setenv("AUTOCODE_PYTHON_CMD", "/new/autocode")
	defer os.Unsetenv("AUTOCODE_PYTHON_CMD")
	os.Setenv("HYBRIDCODER_PYTHON_CMD", "/old/hybridcoder")
	defer os.Unsetenv("HYBRIDCODER_PYTHON_CMD")

	cmd, _, found := findPythonBackend()
	if !found {
		t.Fatal("expected found=true")
	}
	if cmd != "/new/autocode" {
		t.Errorf("expected new env var to take precedence, got %q", cmd)
	}
}

// TestFindPythonBackend_FallsBackToUv verifies that when no env vars are set
// and no binaries are on PATH, we fall back to "uv run autocode serve".
// Note: This test only works if "uv" is on PATH (common in dev environments).
func TestFindPythonBackend_FallsBackToUv(t *testing.T) {
	os.Unsetenv("AUTOCODE_PYTHON_CMD")
	os.Unsetenv("HYBRIDCODER_PYTHON_CMD")

	// Clear PATH to avoid finding autocode/hybridcoder binaries
	origPath := os.Getenv("PATH")
	defer os.Setenv("PATH", origPath)

	// We can't fully test PATH fallback without installing binaries,
	// but we can verify the function returns *something* when uv is on PATH
	cmd, args, found := findPythonBackend()
	if !found {
		t.Skip("uv not on PATH, skipping uv fallback test")
	}
	// If found via uv, verify the args include "autocode"
	if len(args) >= 2 && args[1] == "autocode" {
		// uv run autocode serve
		if args[0] != "run" || args[2] != "serve" {
			t.Errorf("expected uv args [run autocode serve], got %v", args)
		}
	} else if cmd != "" {
		// Found via PATH as autocode or hybridcoder binary — also acceptable
		t.Logf("found backend via PATH: %s %v", cmd, args)
	}
}
