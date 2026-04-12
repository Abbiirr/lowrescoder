package main

import (
	"fmt"
	"strings"
)

type statusBarModel struct {
	Model    string
	Provider string
	Mode     string
	Tokens   int
	Cost     string
	Queue    int
	Width    int
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

	result := strings.Join(parts, " · ")

	if s.Queue > 0 {
		result += fmt.Sprintf(" · queue: %d", s.Queue)
	}

	maxLen := s.Width - 2
	if len(result) > maxLen && maxLen > 10 {
		result = result[:maxLen-1] + "…"
	}

	return statusBarStyle.Render(result)
}
