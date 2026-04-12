package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"runtime"

	"golang.org/x/term"
)

// shouldUseLegacy returns true if the terminal doesn't support the Go TUI
// (dumb terminal or non-interactive stdin).
func shouldUseLegacy() bool {
	// Check for dumb terminal
	if os.Getenv("TERM") == "dumb" {
		return true
	}

	// Check if stdin is a terminal
	if !term.IsTerminal(int(os.Stdin.Fd())) {
		return true
	}

	// Check if stdout is a terminal (avoid TUI in piped/non-interactive output)
	if !term.IsTerminal(int(os.Stdout.Fd())) {
		return true
	}

	return false
}

// findPythonBackend discovers the Python backend command.
// Returns (command, args, found).
//
// Discovery order:
//  1. $AUTOCODE_PYTHON_CMD (or legacy $HYBRIDCODER_PYTHON_CMD)
//  2. "uv run autocode serve" if pyproject.toml exists nearby (dev mode)
//  3. "autocode" on PATH (then legacy "hybridcoder")
//  4. "uv run autocode serve" (fallback)
func findPythonBackend() (string, []string, bool) {
	// 1. Environment variable override (new name, then legacy)
	if cmd := os.Getenv("AUTOCODE_PYTHON_CMD"); cmd != "" {
		return cmd, []string{"serve"}, true
	}
	if cmd := os.Getenv("HYBRIDCODER_PYTHON_CMD"); cmd != "" {
		return cmd, []string{"serve"}, true
	}

	// 2. Dev mode: prefer uv run when pyproject.toml is nearby
	//    This avoids picking up stale system-wide binaries during development.
	uvCmd := "uv"
	if runtime.GOOS == "windows" {
		uvCmd = "uv.exe"
	}
	if _, err := exec.LookPath(uvCmd); err == nil {
		if hasPyprojectToml() {
			return uvCmd, []string{"run", "autocode", "serve"}, true
		}
	}

	// 3. autocode on PATH (then legacy hybridcoder)
	if path, err := exec.LookPath("autocode"); err == nil {
		return path, []string{"serve"}, true
	}
	if path, err := exec.LookPath("hybridcoder"); err == nil {
		return path, []string{"serve"}, true
	}

	// 4. uv run autocode (fallback even without pyproject.toml nearby)
	if _, err := exec.LookPath(uvCmd); err == nil {
		return uvCmd, []string{"run", "autocode", "serve"}, true
	}

	return "", nil, false
}

// hasPyprojectToml checks if pyproject.toml exists in the current directory
// or up to 3 parent directories, indicating we're in a development tree.
func hasPyprojectToml() bool {
	dir, err := os.Getwd()
	if err != nil {
		return false
	}
	for i := 0; i < 4; i++ {
		if _, err := os.Stat(dir + string(os.PathSeparator) + "pyproject.toml"); err == nil {
			return true
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return false
}
