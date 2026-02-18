package main

import "fmt"

// statusBarModel holds data for the status bar at the bottom of the TUI.
type statusBarModel struct {
	Model    string
	Provider string
	Mode     string
	Layer    string
	Tokens   int
	Edits    int
	Queue    int
	Width    int
}

// View renders the status bar as a single line.
func (s statusBarModel) View() string {
	parts := []string{
		fmt.Sprintf("Model: %s", s.Model),
		fmt.Sprintf("Provider: %s", s.Provider),
		fmt.Sprintf("Mode: %s", s.Mode),
	}

	if s.Layer != "" {
		parts = append(parts, s.Layer)
	}

	if s.Queue > 0 {
		parts = append(parts, fmt.Sprintf("Queue: %d", s.Queue))
	}

	if s.Tokens > 0 {
		if s.Tokens >= 1000 {
			parts = append(parts, fmt.Sprintf("Tokens: ~%.1fk", float64(s.Tokens)/1000))
		} else {
			parts = append(parts, fmt.Sprintf("Tokens: ~%d", s.Tokens))
		}
	}

	if s.Edits > 0 {
		parts = append(parts, fmt.Sprintf("Edits: %d", s.Edits))
	}

	var result string
	for i, p := range parts {
		if i > 0 {
			result += " | "
		}
		result += p
	}

	return statusBarStyle.Render(result)
}
