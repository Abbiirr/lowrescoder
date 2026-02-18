package main

import (
	"github.com/charmbracelet/glamour"
)

// renderMarkdownContent renders markdown using Glamour.
// Called ONCE on on_done — never during streaming (per Codex-approved rule).
// Falls back to plain text on error.
func renderMarkdownContent(content string, width int) string {
	if width < 20 {
		width = 80
	}

	renderer, err := glamour.NewTermRenderer(
		glamour.WithAutoStyle(),
		glamour.WithWordWrap(width-2),
	)
	if err != nil {
		return content
	}

	rendered, err := renderer.Render(content)
	if err != nil {
		return content
	}

	return rendered
}
