package main

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
)

// enterAskUser transitions the model to ask-user stage.
func enterAskUser(m model, msg backendAskUserRequestMsg) model {
	m.stage = stageAskUser
	m.askRequestID = msg.RequestID
	m.askQuestion = msg.Question
	m.askOptions = msg.Options
	m.askCursor = 0
	m.askAllowText = msg.AllowText

	if len(msg.Options) == 0 || msg.AllowText {
		// Free-text mode: keep textInput focused
		m.textInput.Focus()
		m.textInput.SetValue("")
		m.textInput.Placeholder = "Type your answer..."
	} else {
		m.textInput.Blur()
	}

	return m
}

// renderAskUserView renders the ask-user prompt.
func renderAskUserView(m model) string {
	var b strings.Builder

	// Question
	b.WriteString(welcomeStyle.Render(m.askQuestion))
	b.WriteString("\n")

	if len(m.askOptions) > 0 {
		// Options mode
		for i, opt := range m.askOptions {
			if i == m.askCursor {
				b.WriteString(approvalActiveStyle.Render(fmt.Sprintf("  ❯ %d. %s", i+1, opt)))
			} else {
				b.WriteString(approvalInactiveStyle.Render(fmt.Sprintf("    %d. %s", i+1, opt)))
			}
			b.WriteString("\n")
		}

		if m.askAllowText {
			b.WriteString(dimStyle.Render("  (or type a custom answer below)"))
			b.WriteString("\n")
			b.WriteString(m.textInput.View())
		}
	} else {
		// Free-text only
		b.WriteString(dimStyle.Render("  (type your answer)"))
		b.WriteString("\n")
		b.WriteString(m.textInput.View())
	}

	return b.String()
}

// handleAskUserKey handles key events during ask-user.
func handleAskUserKey(m model, msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "up", "k":
		if len(m.askOptions) > 0 {
			m.askCursor--
			if m.askCursor < 0 {
				m.askCursor = len(m.askOptions) - 1
			}
		}
		return m, nil

	case "down", "j":
		if len(m.askOptions) > 0 {
			m.askCursor++
			if m.askCursor >= len(m.askOptions) {
				m.askCursor = 0
			}
		}
		return m, nil

	case "enter":
		var answer string

		// If textInput has text and allowText, use that
		if m.askAllowText || len(m.askOptions) == 0 {
			text := strings.TrimSpace(m.textInput.Value())
			if text != "" {
				answer = text
			}
		}

		// If no typed answer, use selected option
		if answer == "" && len(m.askOptions) > 0 {
			answer = m.askOptions[m.askCursor]
		}

		if answer == "" {
			return m, nil
		}

		if m.backend != nil {
			m.backend.SendResponse(m.askRequestID, AskUserResult{Answer: answer})
		}

		m.stage = stageStreaming
		m.textInput.SetValue("")
		m.textInput.Placeholder = "Type a message..."
		m.textInput.Focus()

		return m, tea.Println(dimStyle.Render(fmt.Sprintf("  → %s", answer)))

	case "escape", "esc", "ctrl+c":
		// Default answer
		answer := ""
		if len(m.askOptions) > 0 {
			answer = m.askOptions[0]
		}
		if m.backend != nil {
			m.backend.SendResponse(m.askRequestID, AskUserResult{Answer: answer})
		}

		m.stage = stageStreaming
		m.textInput.SetValue("")
		m.textInput.Placeholder = "Type a message..."
		m.textInput.Focus()

		return m, tea.Println(dimStyle.Render("  → (cancelled)"))

	default:
		// Forward to textInput if in text mode
		if m.askAllowText || len(m.askOptions) == 0 {
			var cmd tea.Cmd
			m.textInput, cmd = m.textInput.Update(msg)
			return m, cmd
		}
	}

	return m, nil
}
