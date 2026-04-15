package main

import (
	"context"
	"flag"
	"fmt"
	"os"

	tea "charm.land/bubbletea/v2"
)

func main() {
	inlineMode := flag.Bool("inline", false, "Run in inline mode (scrollback-friendly, no alternate screen)")
	flag.Parse()

	if shouldUseLegacy() {
		fmt.Fprintln(os.Stderr, "Terminal does not support interactive TUI. Use 'autocode chat' directly.")
		os.Exit(1)
	}

	pythonCmd, pythonArgs, found := findPythonBackend()
	if !found {
		fmt.Fprintln(os.Stderr, "Could not find AutoCode Python backend.")
		fmt.Fprintln(os.Stderr, "Set AUTOCODE_PYTHON_CMD or ensure 'autocode' is on PATH.")
		os.Exit(1)
	}

	backend := NewBackend()

	m := initialModel(backend)
	m.inlineMode = *inlineMode

	// In BubbleTea v2 alt-screen is set per-View via v.AltScreen (see view.go).
	// m.inlineMode controls that field: default = alt-screen, --inline = scrollback.
	p := tea.NewProgram(m)

	ctx := context.Background()
	if err := backend.Start(ctx, p, pythonCmd, pythonArgs); err != nil {
		fmt.Fprintf(os.Stderr, "Failed to start backend: %v\n", err)
		os.Exit(1)
	}

	if sessionID := os.Getenv("AUTOCODE_SESSION_ID"); sessionID != "" {
		backend.SendRequest("session.resume", SessionResumeParams{SessionID: sessionID})
	}

	fmt.Println(welcomeStyle.Render("AutoCode") + dimStyle.Render(" — Edge-native AI coding assistant"))
	fmt.Println(dimStyle.Render("Type a message to start. Use /help for commands, Ctrl+D to quit."))
	fmt.Println()

	// Mode 2026 (synchronized output) is enabled by default in bubbletea v2.

	if _, err := p.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "TUI error: %v\n", err)
	}

	backend.Shutdown()

	fmt.Println(dimStyle.Render("Goodbye!"))
}
