package main

import (
	"context"
	"flag"
	"fmt"
	"os"

	tea "charm.land/bubbletea/v2"
)

func main() {
	// Default is INLINE (Claude-Code-like, scrollback-preserving). Pass
	// --altscreen to opt into the full-screen alternate buffer that takes
	// over the whole terminal while the TUI runs.
	altScreen := flag.Bool("altscreen", false, "Run in alternate-screen mode (takes over the terminal)")
	inlineFlag := flag.Bool("inline", true, "Run in inline mode (default; scrollback-friendly)")
	flag.Parse()
	// If the user passed --altscreen, that wins over the default inline.
	inlineMode := !*altScreen && *inlineFlag

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
	m.inlineMode = inlineMode

	// In BubbleTea v2 alt-screen is set per-View via v.AltScreen (see view.go).
	// m.inlineMode controls that field: default = inline (Claude-Code-like),
	// --altscreen = alt-screen takeover.
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
