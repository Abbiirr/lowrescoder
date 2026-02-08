package main

import (
	"os"
	"os/exec"
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

	return false
}

// findPythonBackend discovers the Python backend command.
// Returns (command, args, found).
//
// Discovery order:
//  1. $HYBRIDCODER_PYTHON_CMD environment variable
//  2. "hybridcoder" on PATH
//  3. "uv run hybridcoder" (for development)
func findPythonBackend() (string, []string, bool) {
	// 1. Environment variable override
	if cmd := os.Getenv("HYBRIDCODER_PYTHON_CMD"); cmd != "" {
		return cmd, []string{"serve"}, true
	}

	// 2. hybridcoder on PATH
	if path, err := exec.LookPath("hybridcoder"); err == nil {
		return path, []string{"serve"}, true
	}

	// 3. uv run hybridcoder (development mode)
	uvCmd := "uv"
	if runtime.GOOS == "windows" {
		uvCmd = "uv.exe"
	}
	if _, err := exec.LookPath(uvCmd); err == nil {
		return uvCmd, []string{"run", "hybridcoder", "serve"}, true
	}

	return "", nil, false
}
