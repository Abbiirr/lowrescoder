package main

import (
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// --- TUI Styles ---

var (
	separatorStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("240"))

	userTurnStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("10")).
			Bold(true)

	streamStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("252"))

	thinkingStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("243")).
			Italic(true)

	toolCallStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("14"))

	toolOKIcon  = lipgloss.NewStyle().Foreground(lipgloss.Color("10")).Render("✓")
	toolErrIcon = lipgloss.NewStyle().Foreground(lipgloss.Color("9")).Render("✗")
	toolWaitIcon = lipgloss.NewStyle().Foreground(lipgloss.Color("11")).Render("⋯")
	toolRunIcon  = lipgloss.NewStyle().Foreground(lipgloss.Color("14")).Render("▶")

	statusBarStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("240"))

	approvalActiveStyle = lipgloss.NewStyle().
				Foreground(lipgloss.Color("10")).
				Bold(true)

	approvalInactiveStyle = lipgloss.NewStyle().
				Foreground(lipgloss.Color("240"))

	errorStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("9")).
			Bold(true)

	welcomeStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("205")).
			Bold(true)

	dimStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("240"))
)

// separator returns a full-width horizontal line.
func separator(width int) string {
	if width < 10 {
		width = 60
	}
	return separatorStyle.Render(strings.Repeat("─", width))
}

// toolIcon returns the appropriate icon for a tool call status.
func toolIcon(status string) string {
	switch status {
	case "completed", "success":
		return toolOKIcon
	case "error":
		return toolErrIcon
	case "running":
		return toolRunIcon
	case "waiting", "pending", "blocked", "denied":
		return toolWaitIcon
	default:
		return toolWaitIcon
	}
}
