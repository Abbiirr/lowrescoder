package main

import (
	"fmt"
	"strings"

	tea "charm.land/bubbletea/v2"
)

// enterApproval transitions the model to approval stage.
func enterApproval(m model, msg backendApprovalRequestMsg) model {
	m.stage = stageApproval
	m.approvalRequestID = msg.RequestID
	m.approvalTool = msg.Tool
	m.approvalArgs = msg.Args
	m.approvalCursor = 0
	m.composer.Blur()
	return m
}

// renderApprovalView renders a compact Claude-like approval prompt.
func renderApprovalView(m model) string {
	var b strings.Builder

	// Compact tool + args header (single ● prefix line)
	b.WriteString(accentStyle.Render("●") + " " + toolCallStyle.Render(titleCase(m.approvalTool)))

	// Show compact args summary (single line if short, otherwise truncated)
	if m.approvalArgs != "" {
		args := strings.TrimSpace(m.approvalArgs)
		// Flatten to single line for compact display
		flat := strings.ReplaceAll(args, "\n", " ")
		if len(flat) > 60 {
			flat = flat[:57] + "..."
		}
		b.WriteString(" " + dimStyle.Render(flat))
	}
	b.WriteString("\n")

	// Compact option list with cursor
	for i, opt := range m.approvalOptions {
		if i == m.approvalCursor {
			b.WriteString(approvalActiveStyle.Render(fmt.Sprintf("  ❯ %s", opt)))
		} else {
			b.WriteString(approvalInactiveStyle.Render(fmt.Sprintf("    %s", opt)))
		}
		b.WriteString("\n")
	}

	return b.String()
}

// titleCase converts snake_case to Title Case.
func titleCase(s string) string {
	parts := strings.Split(s, "_")
	for i, p := range parts {
		if len(p) > 0 {
			parts[i] = strings.ToUpper(p[:1]) + p[1:]
		}
	}
	return strings.Join(parts, " ")
}

// handleApprovalKey handles key events during approval.
func handleApprovalKey(m model, msg tea.KeyPressMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "up", "k":
		m.approvalCursor--
		if m.approvalCursor < 0 {
			m.approvalCursor = len(m.approvalOptions) - 1
		}
		return m, nil

	case "down", "j":
		m.approvalCursor++
		if m.approvalCursor >= len(m.approvalOptions) {
			m.approvalCursor = 0
		}
		return m, nil

	case "enter":
		selected := m.approvalOptions[m.approvalCursor]
		var result ApprovalResult

		switch selected {
		case "Yes":
			result = ApprovalResult{Approved: true}
		case "Yes, this session":
			result = ApprovalResult{Approved: true, SessionApprove: true}
		default: // "No"
			result = ApprovalResult{Approved: false}
		}

		if m.backend != nil {
			m.backend.SendResponse(m.approvalRequestID, result)
		}
		m.stage = stageStreaming
		m.composer.Focus()

		return m, tea.Println(dimStyle.Render(fmt.Sprintf("  → %s", selected)))

	case "escape", "esc", "ctrl+c":
		// Deny
		if m.backend != nil {
			m.backend.SendResponse(m.approvalRequestID, ApprovalResult{Approved: false})
		}
		m.stage = stageStreaming
		m.composer.Focus()
		return m, tea.Println(dimStyle.Render("  → Denied"))
	}

	return m, nil
}
