package main

import (
	"fmt"
	"strings"
)

// renderTaskPanel renders a compact task panel showing tasks and subagents.
// Returns empty string if there are no tasks or subagents to show.
func renderTaskPanel(tasks []taskEntry, subagents []subagentEntry, width int) string {
	if len(tasks) == 0 && len(subagents) == 0 {
		return ""
	}

	var b strings.Builder

	// Tasks
	for _, t := range tasks {
		icon := taskIcon(t.Status)
		line := fmt.Sprintf(" %s %s", icon, t.Title)
		if width > 0 && len(line) > width-1 {
			line = line[:width-4] + "..."
		}
		b.WriteString(line)
		b.WriteString("\n")
	}

	// Subagents
	for _, sa := range subagents {
		saType := sa.Type
		if saType == "" {
			saType = "?"
		}
		summary := sa.Summary
		if len(summary) > 60 {
			summary = summary[:57] + "..."
		}
		var line string
		if sa.Status == "running" {
			line = fmt.Sprintf(" [%s %s] %s", sa.ID, saType, summary)
		} else {
			line = fmt.Sprintf(" [%s %s] %s: %s", sa.ID, saType, sa.Status, summary)
		}
		if width > 0 && len(line) > width-1 {
			line = line[:width-4] + "..."
		}
		b.WriteString(dimStyle.Render(line))
		b.WriteString("\n")
	}

	return b.String()
}

// taskIcon returns a checkbox icon for a task status.
func taskIcon(status string) string {
	switch status {
	case "completed":
		return "[x]"
	case "in_progress":
		return "[>]"
	default:
		return "[ ]"
	}
}
