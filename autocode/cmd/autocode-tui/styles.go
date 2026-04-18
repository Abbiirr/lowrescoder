package main

import (
	"strings"

	"charm.land/lipgloss/v2"
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

	toolOKIcon   = lipgloss.NewStyle().Foreground(lipgloss.Color("10")).Render("✓")
	toolErrIcon  = lipgloss.NewStyle().Foreground(lipgloss.Color("9")).Render("✗")
	toolWaitIcon = lipgloss.NewStyle().Foreground(lipgloss.Color("11")).Render("⋯")
	toolRunIcon  = lipgloss.NewStyle().Foreground(lipgloss.Color("14")).Render("▶")

	statusBarStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("240"))

	// branchPillStyle renders the git branch as a compact right-side pill
	// in the status bar, matching Claude Code's bottom-right branch tag.
	branchPillStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("15")).
			Background(lipgloss.Color("#0e7e9a")).
			Bold(true)

	// modeHintStyle renders the bottom "mode · (shift+tab to cycle)" line.
	modeHintStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("245")).
			Italic(true)

	approvalActiveStyle = lipgloss.NewStyle().
				Foreground(lipgloss.Color("10")).
				Bold(true)

	approvalInactiveStyle = lipgloss.NewStyle().
				Foreground(lipgloss.Color("240"))

	errorStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("9")).
			Bold(true)

	// Accent color: #cc7832 (amber/orange) — Claude Code parity
	accentStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#cc7832")).
			Bold(true)

	welcomeStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#cc7832")).
			Bold(true)

	dimStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("240"))

	// Composer frame styles (stage-colored bars)
	composerFrameIdleStyle = lipgloss.NewStyle().
				Foreground(lipgloss.Color("240"))

	composerFrameStreamingStyle = lipgloss.NewStyle().
					Foreground(lipgloss.Color("#cc7832"))

	composerFrameApprovalStyle = lipgloss.NewStyle().
					Foreground(lipgloss.Color("11"))

	composerFrameAskUserStyle = lipgloss.NewStyle().
					Foreground(lipgloss.Color("14"))

	composerTitleStyle = lipgloss.NewStyle().
				Foreground(lipgloss.Color("240"))

	composerHintStyle = lipgloss.NewStyle().
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
