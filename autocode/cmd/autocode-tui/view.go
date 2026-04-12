package main

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// View renders the live area (never the scrollback).
// O(1) — only renders what's currently active on screen.
func (m model) View() string {
	if m.quitting {
		return ""
	}

	var b strings.Builder

	// 0. Header (compact branded header)
	if m.stage == stageInput && len(m.toolCalls) == 0 && m.streamBuf.Len() == 0 {
		b.WriteString(accentStyle.Render("\u25c6") + " AutoCode\n")
		b.WriteString(dimStyle.Render("/help for help, /model to switch, Ctrl+D to quit"))
		b.WriteString("\n")
	}

	// 1. Thinking tokens (if showing and non-empty)
	b.WriteString(renderThinking(m))

	// 2. Task panel (only during active work, demoted in quiet chat-first state)
	if m.stage == stageStreaming {
		if taskPanel := renderTaskPanel(m.taskPanelTasks, m.taskPanelSubagents, m.width); taskPanel != "" {
			b.WriteString(taskPanel)
		}
	}

	// 3. Tool call log (current turn)
	b.WriteString(renderToolArea(m))

	// 4. Streaming text (plain text — no Glamour during streaming)
	b.WriteString(renderStreamArea(m))

	// 5. Error display
	if m.lastError != "" {
		b.WriteString(errorStyle.Render("Error: " + m.lastError))
		b.WriteString("\n")
	}

	// 6. Autocomplete dropdown (when multiple matches) — with cursor highlight
	if len(m.completions) > 1 {
		b.WriteString(renderCompletionDropdown(m.completions, m.width, m.completionCursor))
	}

	// 7. Input area (depends on stage)
	switch m.stage {
	case stageApproval:
		b.WriteString(separator(m.width))
		b.WriteString("\n")
		b.WriteString(renderApprovalView(m))
	case stageAskUser:
		b.WriteString(separator(m.width))
		b.WriteString("\n")
		b.WriteString(renderAskUserView(m))
	case stageModelPicker:
		b.WriteString(separator(m.width))
		b.WriteString("\n")
		b.WriteString(renderModelPicker(m))
	case stageProviderPicker:
		b.WriteString(separator(m.width))
		b.WriteString("\n")
		b.WriteString(renderProviderPicker(m))
	case stagePalette:
		b.WriteString(separator(m.width))
		b.WriteString("\n")
		b.WriteString(renderPaletteView(m))
	default:
		if m.claudeLike {
			// Queue preview + composer slab (includes its own top/bottom bars)
			b.WriteString(renderQueuePreview(m))
			b.WriteString(renderComposer(m))
		} else {
			// Default profile: simple separator + textarea (no frame)
			b.WriteString(separator(m.width))
			b.WriteString("\n")
			b.WriteString(m.composer.View())
		}
	}
	b.WriteString("\n")

	// 8. Status bar
	m.statusBar.Queue = len(m.messageQueue)
	b.WriteString(m.statusBar.View())

	return b.String()
}

// renderThinking renders the last 5 lines of thinking tokens.
func renderThinking(m model) string {
	if !m.showThinking || m.thinkingBuf.Len() == 0 {
		return ""
	}
	content := m.thinkingBuf.String()
	lines := strings.Split(content, "\n")
	if len(lines) > 5 {
		lines = lines[len(lines)-5:]
	}
	return thinkingStyle.Render(strings.Join(lines, "\n")) + "\n"
}

// renderToolArea renders the tool call log for the current turn.
func renderToolArea(m model) string {
	if len(m.toolCalls) == 0 {
		return ""
	}
	var b strings.Builder
	for _, tc := range m.toolCalls {
		icon := toolIcon(tc.Status)
		line := fmt.Sprintf(" \u23bf %s %s", icon, toolCallStyle.Render(tc.Name))
		if tc.Status == "error" && tc.Result != "" {
			errText := tc.Result
			maxResult := m.width - len(tc.Name) - 10
			if maxResult < 20 {
				maxResult = 20
			}
			if len(errText) > maxResult {
				errText = errText[:maxResult-3] + "..."
			}
			line += " " + errorStyle.Render(errText)
		} else if tc.Status == "completed" && tc.Result != "" {
			result := tc.Result
			maxResult := m.width - len(tc.Name) - 10
			if maxResult < 20 {
				maxResult = 20
			}
			if len(result) > maxResult {
				result = result[:maxResult-3] + "..."
			}
			line += " " + dimStyle.Render(result)
		}
		b.WriteString(line)
		b.WriteString("\n")
	}
	return b.String()
}

// renderStreamArea renders the streaming text area.
func renderStreamArea(m model) string {
	if m.stage != stageStreaming {
		return ""
	}
	var b strings.Builder
	content := m.streamBuf.String()
	if content == "" && m.tokenBuf.Len() == 0 {
		// Show spinner while waiting for first token
		b.WriteString(m.spin.View() + dimStyle.Render(" Thinking\u2026") + "\n")
	} else {
		// Cap displayed content (show last 50 lines)
		displayed := content
		if m.tokenBuf.Len() > 0 {
			displayed += m.tokenBuf.String()
		}
		lines := strings.Split(displayed, "\n")
		if len(lines) > 50 {
			b.WriteString(dimStyle.Render(fmt.Sprintf("[%d lines above]\n", len(lines)-50)))
			lines = lines[len(lines)-50:]
		}
		b.WriteString(streamStyle.Render(strings.Join(lines, "\n")))
		b.WriteString("\n")
	}
	return b.String()
}

// renderCompletionDropdown renders a dropdown of completion options.
// The cursor index (0-based) indicates which entry is highlighted — that
// entry is rendered in a highlighted style so users can see which one will
// be accepted by Enter or Tab.
func renderCompletionDropdown(completions []string, width int, cursor int) string {
	var b strings.Builder

	// Cap at 8 visible items, windowing the cursor so it stays visible
	const visible = 8
	start := 0
	if len(completions) > visible {
		start = cursor - visible/2
		if start < 0 {
			start = 0
		}
		if start+visible > len(completions) {
			start = len(completions) - visible
		}
	}
	end := start + visible
	if end > len(completions) {
		end = len(completions)
	}

	for i := start; i < end; i++ {
		item := completions[i]
		if i == cursor {
			b.WriteString("  " + approvalActiveStyle.Render("\u276f "+item))
		} else {
			b.WriteString("    " + dimStyle.Render(item))
		}
		b.WriteString("\n")
	}

	if len(completions) > visible {
		b.WriteString(dimStyle.Render(fmt.Sprintf("  [%d/%d]", cursor+1, len(completions))))
		b.WriteString("\n")
	}

	return b.String()
}

// renderPaletteView renders the command palette overlay.
func renderPaletteView(m model) string {
	var b strings.Builder

	headerStyle := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#cc7832"))
	activeStyle := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("10"))
	inactiveStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("252"))
	descStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("240"))
	filterStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("14"))

	b.WriteString(headerStyle.Render("◆ Command Palette"))
	b.WriteString("  ")
	if m.paletteFilter != "" {
		b.WriteString(filterStyle.Render(m.paletteFilter))
	} else {
		b.WriteString(dimStyle.Render("type to filter…"))
	}
	b.WriteString("\n")

	descs := paletteDescMap()

	maxShow := 10
	matches := m.paletteMatches
	if len(matches) > maxShow {
		matches = matches[:maxShow]
	}

	for i, cmd := range matches {
		prefix := "  "
		style := inactiveStyle
		if i == m.paletteCursor {
			prefix = "❯ "
			style = activeStyle
		}
		desc := descs[cmd]
		line := fmt.Sprintf("%s%-16s %s", prefix, style.Render(cmd), descStyle.Render(desc))
		b.WriteString(line)
		b.WriteString("\n")
	}

	if len(m.paletteMatches) > maxShow {
		b.WriteString(dimStyle.Render(fmt.Sprintf("  … and %d more", len(m.paletteMatches)-maxShow)))
		b.WriteString("\n")
	}

	if len(m.paletteMatches) == 0 {
		b.WriteString(dimStyle.Render("  No matching commands"))
		b.WriteString("\n")
	}

	b.WriteString(dimStyle.Render("  ↑↓ navigate · enter select · esc close"))

	return b.String()
}
