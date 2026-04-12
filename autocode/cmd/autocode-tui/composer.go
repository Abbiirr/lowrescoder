package main

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/key"
	"github.com/charmbracelet/bubbles/textarea"
	"github.com/charmbracelet/lipgloss"
)

const (
	composerMinH = 3
	composerMaxH = 8
)

// newComposer creates a textarea configured as a chat composer.
func newComposer(width int) textarea.Model {
	ta := textarea.New()
	ta.Placeholder = "Ask AutoCode\u2026"
	ta.Prompt = "\u276f "
	ta.ShowLineNumbers = false
	ta.CharLimit = 4000
	ta.MaxHeight = composerMaxH
	ta.SetHeight(composerMinH)

	// Minimal styling — no highlight on cursor line
	ta.FocusedStyle.CursorLine = lipgloss.NewStyle()
	ta.FocusedStyle.Placeholder = lipgloss.NewStyle().Foreground(lipgloss.Color("240"))
	ta.FocusedStyle.Prompt = lipgloss.NewStyle().Foreground(lipgloss.Color("10"))
	ta.FocusedStyle.Text = lipgloss.NewStyle()
	ta.BlurredStyle.CursorLine = lipgloss.NewStyle()
	ta.BlurredStyle.Placeholder = lipgloss.NewStyle().Foreground(lipgloss.Color("240"))
	ta.BlurredStyle.Prompt = lipgloss.NewStyle().Foreground(lipgloss.Color("240"))
	ta.BlurredStyle.Text = lipgloss.NewStyle().Foreground(lipgloss.Color("240"))

	// Rebind: Enter sends (intercepted by us), Alt+Enter/Ctrl+J inserts newline
	ta.KeyMap.InsertNewline = key.NewBinding(
		key.WithKeys("alt+enter", "ctrl+j"),
		key.WithHelp("alt+enter", "new line"),
	)

	composerSetWidth(&ta, width)
	ta.Focus()

	return ta
}

// composerValue returns the trimmed text from the composer.
func composerValue(m *model) string {
	return strings.TrimSpace(m.composer.Value())
}

// composerClear resets the composer content and height.
func composerClear(m *model) {
	m.composer.SetValue("")
	m.composer.SetHeight(composerMinH)
}

// composerFocus focuses the composer.
func composerFocus(m *model) {
	m.composer.Focus()
}

// composerSetWidth adjusts the textarea width for the terminal width.
func composerSetWidth(ta *textarea.Model, totalWidth int) {
	inner := totalWidth - 4 // padding and border allowance
	if inner < 20 {
		inner = 20
	}
	ta.SetWidth(inner)
}

// composerAutoHeight adjusts composer height based on content.
func composerAutoHeight(m *model) {
	lines := m.composer.LineCount()
	h := lines + 1 // extra line for typing room
	if h < composerMinH {
		h = composerMinH
	}
	if h > composerMaxH {
		h = composerMaxH
	}
	m.composer.SetHeight(h)
}

// renderComposer renders the full composer slab with frame and hints.
func renderComposer(m model) string {
	var b strings.Builder
	w := m.width
	if w < 30 {
		w = 60
	}

	// Frame bars colored by stage
	frame := composerFrameStyle(m.stage)
	bar := frame.Render(strings.Repeat("\u2500", w-2))

	// Top bar
	b.WriteString(bar)
	b.WriteString("\n")

	// Title
	b.WriteString(composerTitleStyle.Render(" autocode"))
	b.WriteString("\n")

	// Textarea body
	b.WriteString(m.composer.View())
	b.WriteString("\n")

	// Hints
	b.WriteString(composerHintStyle.Render(" Enter send \u00b7 Alt+Enter newline \u00b7 Esc cancel \u00b7 / commands \u00b7 @ files"))
	b.WriteString("\n")

	// Bottom bar
	b.WriteString(bar)

	return b.String()
}

// renderQueuePreview renders pending queued messages above the composer.
func renderQueuePreview(m model) string {
	if len(m.messageQueue) == 0 {
		return ""
	}

	var b strings.Builder
	b.WriteString(dimStyle.Render(" Queued:"))
	b.WriteString("\n")
	for _, msg := range m.messageQueue {
		preview := msg
		if len(preview) > 60 {
			preview = preview[:57] + "..."
		}
		b.WriteString(dimStyle.Render(fmt.Sprintf("  \u2022 %s", preview)))
		b.WriteString("\n")
	}
	return b.String()
}

// composerFrameStyle returns the bar style for the current stage.
func composerFrameStyle(s stage) lipgloss.Style {
	switch s {
	case stageStreaming:
		return composerFrameStreamingStyle
	case stageApproval:
		return composerFrameApprovalStyle
	case stageAskUser:
		return composerFrameAskUserStyle
	default:
		return composerFrameIdleStyle
	}
}
