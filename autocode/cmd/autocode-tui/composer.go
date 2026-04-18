package main

import (
	"strings"

	"charm.land/bubbles/v2/key"
	"charm.land/bubbles/v2/textarea"
	"charm.land/lipgloss/v2"
)

// Composer height: start at 1 row (single `❯` prompt — Claude Code / Pi
// shape) and grow up to composerMaxH as the user adds multi-line content
// via Alt+Enter.
const (
	composerMinH = 1
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
	ta.SetStyles(textarea.Styles{
		Focused: textarea.StyleState{
			CursorLine:  lipgloss.NewStyle(),
			Placeholder: lipgloss.NewStyle().Foreground(lipgloss.Color("240")),
			Prompt:      lipgloss.NewStyle().Foreground(lipgloss.Color("10")),
			Text:        lipgloss.NewStyle(),
		},
		Blurred: textarea.StyleState{
			CursorLine:  lipgloss.NewStyle(),
			Placeholder: lipgloss.NewStyle().Foreground(lipgloss.Color("240")),
			Prompt:      lipgloss.NewStyle().Foreground(lipgloss.Color("240")),
			Text:        lipgloss.NewStyle().Foreground(lipgloss.Color("240")),
		},
	})

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
// Height tracks line count exactly (clamped to [composerMinH, composerMaxH])
// so a single-line prompt shows one `❯` row, not two.
func composerAutoHeight(m *model) {
	h := m.composer.LineCount()
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
