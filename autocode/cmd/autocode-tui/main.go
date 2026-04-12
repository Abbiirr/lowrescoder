package main

import (
	"context"
	"fmt"
	"os"

	tea "github.com/charmbracelet/bubbletea"
)

func main() {
	// Check terminal compatibility
	if shouldUseLegacy() {
		fmt.Fprintln(os.Stderr, "Terminal does not support interactive TUI. Use 'autocode chat' directly.")
		os.Exit(1)
	}

	// Find Python backend
	pythonCmd, pythonArgs, found := findPythonBackend()
	if !found {
		fmt.Fprintln(os.Stderr, "Could not find AutoCode Python backend.")
		fmt.Fprintln(os.Stderr, "Set AUTOCODE_PYTHON_CMD or ensure 'autocode' is on PATH.")
		os.Exit(1)
	}

	// Create backend
	backend := NewBackend()

	// Create Bubble Tea program
	m := initialModel(backend)
	p := tea.NewProgram(
		m,
		// No tea.WithAltScreen() — inline mode preserves native scrollback
		tea.WithMouseCellMotion(),
	)

	// Start backend with program reference
	ctx := context.Background()
	if err := backend.Start(ctx, p, pythonCmd, pythonArgs); err != nil {
		fmt.Fprintf(os.Stderr, "Failed to start backend: %v\n", err)
		os.Exit(1)
	}

	// Optional session resume injected by the Python CLI wrapper.
	if sessionID := os.Getenv("AUTOCODE_SESSION_ID"); sessionID != "" {
		backend.SendRequest("session.resume", SessionResumeParams{SessionID: sessionID})
	}

	// Print welcome banner (above the live area)
	fmt.Println(welcomeStyle.Render("AutoCode") + dimStyle.Render(" — Edge-native AI coding assistant"))
	fmt.Println(dimStyle.Render("Type a message to start. Use /help for commands, Ctrl+D to quit."))
	fmt.Println()

	// Run the TUI
	if _, err := p.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "TUI error: %v\n", err)
	}

	// Shutdown
	backend.Shutdown()

	fmt.Println(dimStyle.Render("Goodbye!"))
}
