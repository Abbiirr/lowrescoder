package main

import (
	"fmt"
	"strings"
)

// View renders the live area (never the scrollback).
// O(1) — only renders what's currently active on screen.
func (m model) View() string {
	if m.quitting {
		return ""
	}

	var b strings.Builder

	// 1. Thinking tokens (if showing and non-empty)
	if m.showThinking && m.thinkingBuf.Len() > 0 {
		content := m.thinkingBuf.String()
		// Show last 5 lines of thinking to avoid taking too much space
		lines := strings.Split(content, "\n")
		if len(lines) > 5 {
			lines = lines[len(lines)-5:]
		}
		b.WriteString(thinkingStyle.Render(strings.Join(lines, "\n")))
		b.WriteString("\n")
	}

	// 2. Task panel (between thinking and tool calls)
	if taskPanel := renderTaskPanel(m.taskPanelTasks, m.taskPanelSubagents, m.width); taskPanel != "" {
		b.WriteString(taskPanel)
	}

	// 3. Tool call log (current turn)
	for _, tc := range m.toolCalls {
		icon := toolIcon(tc.Status)
		line := fmt.Sprintf(" %s %s", icon, toolCallStyle.Render(tc.Name))
		if tc.Status == "error" && tc.Result != "" {
			line += " " + errorStyle.Render(tc.Result)
		} else if tc.Status == "completed" && tc.Result != "" {
			// Truncate long results
			result := tc.Result
			if len(result) > 100 {
				result = result[:97] + "..."
			}
			line += " " + dimStyle.Render(result)
		}
		b.WriteString(line)
		b.WriteString("\n")
	}

	// 4. Streaming text (plain text — no Glamour during streaming)
	if m.stage == stageStreaming {
		content := m.streamBuf.String()
		if content == "" && m.tokenBuf.Len() == 0 {
			// Show spinner while waiting for first token
			b.WriteString(m.spin.View() + " Thinking...\n")
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
	}

	// 5. Error display
	if m.lastError != "" {
		b.WriteString(errorStyle.Render("Error: " + m.lastError))
		b.WriteString("\n")
	}

	// 6. Autocomplete dropdown (when multiple matches)
	if len(m.completions) > 1 {
		b.WriteString(renderCompletionDropdown(m.completions, m.width))
	}

	// 7. Separator line
	b.WriteString(separator(m.width))
	b.WriteString("\n")

	// 8. Input area (depends on stage)
	switch m.stage {
	case stageApproval:
		b.WriteString(renderApprovalView(m))
	case stageAskUser:
		b.WriteString(renderAskUserView(m))
	default:
		b.WriteString(m.textInput.View())
	}
	b.WriteString("\n")

	// 9. Status bar
	m.statusBar.Queue = len(m.messageQueue)
	b.WriteString(m.statusBar.View())

	return b.String()
}

// renderCompletionDropdown renders a dropdown of completion options.
func renderCompletionDropdown(completions []string, width int) string {
	var b strings.Builder

	// Cap at 8 items
	items := completions
	if len(items) > 8 {
		items = items[:8]
	}

	// Determine column layout: 2 columns if width allows
	colWidth := 20
	cols := 1
	if width > 50 {
		cols = 2
	}

	for i := 0; i < len(items); i += cols {
		b.WriteString("  ")
		for c := 0; c < cols && i+c < len(items); c++ {
			item := items[i+c]
			padded := item
			if len(padded) < colWidth {
				padded += strings.Repeat(" ", colWidth-len(padded))
			}
			b.WriteString(dimStyle.Render(padded))
		}
		b.WriteString("\n")
	}

	return b.String()
}
