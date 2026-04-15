package main

import (
	"fmt"
	"strings"

	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"
)

// View renders the live area.
// Stable scrollback lines are emitted via tea.Println and never redrawn.
// BubbleTea v2 with Mode 2026 handles terminal-level differential rendering automatically.
func (m model) View() tea.View {
	if m.quitting {
		return tea.NewView("")
	}

	var b strings.Builder

	// 0. Header (compact branded header or startup indicator)
	if m.stage == stageInit || (m.stage == stageInput && len(m.toolCalls) == 0 && m.streamBuf.Len() == 0) {
		b.WriteString(accentStyle.Render("\u25c6") + " AutoCode\n")
		if m.stage == stageInit {
			b.WriteString(m.spin.View() + " " + dimStyle.Render("Connecting to backend…"))
		} else {
			b.WriteString(dimStyle.Render("/help for help, /model to switch, Ctrl+D to quit"))
		}
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

	// 7. Steer input overlay (Phase 4)
	if m.stage == stageSteer {
		b.WriteString(renderSteerView(m))
		b.WriteString("\n")
	}

	// 8. Input area (depends on stage)
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
	case stageSteer:
		// steer view already rendered above
	default:
		if m.claudeLike {
			b.WriteString(renderQueuePreview(m))
			b.WriteString(renderComposer(m))
		} else {
			b.WriteString(separator(m.width))
			b.WriteString("\n")
			b.WriteString(m.composer.View())
		}
	}
	b.WriteString("\n")

	// 9. Plan mode indicator (Phase 5)
	if m.planMode {
		b.WriteString(planModeStyle.Render(" [PLAN MODE] "))
		b.WriteString("\n")
	}

	// 10. Task dashboard footer (Phase 5)
	b.WriteString(renderTaskDashboard(m))

	// 11. Status bar
	m.statusBar.Queue = len(m.messageQueue) + len(m.followupQueue)
	m.statusBar.SessionID = m.sessionID
	m.statusBar.BackgroundTasks = m.backgroundTasks
	b.WriteString(m.statusBar.View())

	v := tea.NewView(b.String())
	v.MouseMode = tea.MouseModeCellMotion
	v.AltScreen = !m.inlineMode // default: alt-screen; --inline: scrollback-preserving inline mode
	return v
}

// renderThinking renders thinking tokens with a Claude Code style header.
func renderThinking(m model) string {
	if !m.showThinking || m.thinkingBuf.Len() == 0 {
		return ""
	}
	var b strings.Builder
	content := m.thinkingBuf.String()
	lines := strings.Split(content, "\n")

	// Header: "Thinking…" in dim style
	b.WriteString(dimStyle.Render("  ▸ Thinking…"))
	b.WriteString("\n")

	// Show last 5 lines, indented and dimmed
	if len(lines) > 5 {
		lines = lines[len(lines)-5:]
	}
	for _, line := range lines {
		if strings.TrimSpace(line) == "" {
			continue
		}
		rendered := line
		if len(rendered) > 120 {
			rendered = rendered[:117] + "..."
		}
		b.WriteString(thinkingStyle.Render("  │ " + rendered))
		b.WriteString("\n")
	}
	return b.String()
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
		b.WriteString(m.spin.View() + " " + accentStyle.Render(m.currentVerb+"…") + "\n")
	} else {
		displayed := content
		if m.tokenBuf.Len() > 0 {
			displayed += m.tokenBuf.String()
		}
		if m.stableScrollbackLines != nil {
			displayed = dimStyle.Render(fmt.Sprintf("[%d lines above]\n", len(m.stableScrollbackLines))) + displayed
		}
		b.WriteString(streamStyle.Render(displayed))
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

// --- Phase 4: Steer view ---

// planModeStyle renders the plan mode indicator.
var planModeStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("11")).Background(lipgloss.Color("236"))

// renderSteerView renders the steer input overlay during streaming.
func renderSteerView(m model) string {
	var b strings.Builder
	b.WriteString(separator(m.width))
	b.WriteString("\n")
	b.WriteString(accentStyle.Render("  ⚡ Steer: "))
	b.WriteString(m.steerInput)
	b.WriteString("▏")
	b.WriteString("\n")
	b.WriteString(dimStyle.Render("  Enter to send · Esc to cancel"))
	b.WriteString("\n")
	return b.String()
}

// --- Phase 5: Task dashboard ---

// renderTaskDashboard renders a compact task dashboard in the footer area.
func renderTaskDashboard(m model) string {
	if len(m.taskPanelTasks) == 0 {
		return ""
	}
	pending := 0
	running := 0
	done := 0
	failed := 0
	for _, t := range m.taskPanelTasks {
		switch t.Status {
		case "pending":
			pending++
		case "running":
			running++
		case "done", "completed":
			done++
		case "failed", "error":
			failed++
		}
	}
	var parts []string
	if pending > 0 {
		parts = append(parts, fmt.Sprintf("⏳ %d pending", pending))
	}
	if running > 0 {
		parts = append(parts, fmt.Sprintf("▶ %d running", running))
	}
	if done > 0 {
		parts = append(parts, fmt.Sprintf("✓ %d done", done))
	}
	if failed > 0 {
		parts = append(parts, fmt.Sprintf("✗ %d failed", failed))
	}
	if len(parts) == 0 {
		return ""
	}
	return dimStyle.Render("  "+strings.Join(parts, " · ")) + "\n"
}
