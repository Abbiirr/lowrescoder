package main

import (
	"fmt"
	"os/exec"
	"strings"
)

type statusBarModel struct {
	Model           string
	Provider        string
	Mode            string
	Tokens          int
	Cost            string
	Queue           int
	SessionID       string
	BackgroundTasks int
	Branch          string // git branch, populated once at startup
	Width           int
}

// detectGitBranch returns the current git branch (or "" if not a repo).
// Called once at startup; the result is cached on the statusBar.
func detectGitBranch() string {
	cmd := exec.Command("git", "rev-parse", "--abbrev-ref", "HEAD")
	out, err := cmd.Output()
	if err != nil {
		return ""
	}
	branch := strings.TrimSpace(string(out))
	if branch == "HEAD" {
		// Detached HEAD: fall back to short SHA
		shaOut, shaErr := exec.Command("git", "rev-parse", "--short", "HEAD").Output()
		if shaErr == nil {
			return strings.TrimSpace(string(shaOut))
		}
		return ""
	}
	return branch
}

func (s statusBarModel) View() string {
	if s.Width < 10 {
		s.Width = 60
	}

	parts := []string{}
	if s.Model != "" && s.Model != "..." {
		parts = append(parts, s.Model)
	}
	if s.Provider != "" {
		parts = append(parts, s.Provider)
	}
	if s.Mode != "" {
		parts = append(parts, s.Mode)
	}
	if s.Tokens > 0 {
		if s.Tokens >= 1000 {
			parts = append(parts, fmt.Sprintf("%.1fk tokens", float64(s.Tokens)/1000))
		} else {
			parts = append(parts, fmt.Sprintf("%d tokens", s.Tokens))
		}
	}
	if s.Cost != "" {
		parts = append(parts, s.Cost)
	}
	if s.SessionID != "" {
		parts = append(parts, s.SessionID)
	}

	result := strings.Join(parts, " · ")

	if s.Queue > 0 {
		result += fmt.Sprintf(" · queue: %d", s.Queue)
	}
	if s.BackgroundTasks > 0 {
		result += fmt.Sprintf(" · ⏳ %d bg", s.BackgroundTasks)
	}

	// Git branch pill, right-justified when width allows it.
	var rightPill string
	if s.Branch != "" {
		rightPill = branchPillStyle.Render(" " + s.Branch + " ")
	}

	maxLen := s.Width - 2 - lipglossWidth(rightPill) - 2
	if len(result) > maxLen && maxLen > 10 {
		result = result[:maxLen-1] + "…"
	}

	rendered := statusBarStyle.Render(result)
	if rightPill != "" {
		pad := s.Width - lipglossWidth(rendered) - lipglossWidth(rightPill)
		if pad < 1 {
			pad = 1
		}
		rendered = rendered + strings.Repeat(" ", pad) + rightPill
	}
	return rendered
}

// lipglossWidth is a crude visible-width approximation that strips ANSI
// escapes so we can right-align the branch pill without the escape bytes
// being counted as characters.
func lipglossWidth(s string) int {
	// Strip CSI ... m sequences using a minimal state machine.
	width := 0
	inEsc := false
	for _, r := range s {
		if inEsc {
			if r == 'm' {
				inEsc = false
			}
			continue
		}
		if r == 0x1b {
			inEsc = true
			continue
		}
		width++
	}
	return width
}
