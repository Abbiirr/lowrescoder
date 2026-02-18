package main

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
)

// enterApproval transitions the model to approval stage.
func enterApproval(m model, msg backendApprovalRequestMsg) model {
	m.stage = stageApproval
	m.approvalRequestID = msg.RequestID
	m.approvalTool = msg.Tool
	m.approvalArgs = msg.Args
	m.approvalCursor = 0
	m.textInput.Blur()
	return m
}

// renderApprovalView renders the approval prompt.
func renderApprovalView(m model) string {
	var b strings.Builder

	// Tool name and args summary
	b.WriteString(toolCallStyle.Render(fmt.Sprintf("Tool: %s", m.approvalTool)))
	b.WriteString("\n")

	// Show args (truncated)
	if m.approvalArgs != "" {
		args := m.approvalArgs
		lines := strings.Split(args, "\n")
		if len(lines) > 5 {
			lines = lines[:5]
			lines = append(lines, "  ...")
		}
		for _, line := range lines {
			if len(line) > 80 {
				line = line[:77] + "..."
			}
			b.WriteString(dimStyle.Render("  " + line))
			b.WriteString("\n")
		}
	}

	b.WriteString("\n")
	b.WriteString("Allow?\n")

	// Option list with cursor
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

// handleApprovalKey handles key events during approval.
func handleApprovalKey(m model, msg tea.KeyMsg) (tea.Model, tea.Cmd) {
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
		m.textInput.Focus()

		return m, tea.Println(dimStyle.Render(fmt.Sprintf("  → %s", selected)))

	case "escape", "esc", "ctrl+c":
		// Deny
		if m.backend != nil {
			m.backend.SendResponse(m.approvalRequestID, ApprovalResult{Approved: false})
		}
		m.stage = stageStreaming
		m.textInput.Focus()
		return m, tea.Println(dimStyle.Render("  → Denied"))
	}

	return m, nil
}
