package main

import (
	"fmt"
	"strings"

	tea "charm.land/bubbletea/v2"
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
		// Free-text mode: keep composer focused
		m.composer.Focus()
		m.composer.SetValue("")
		m.composer.Placeholder = "Type your answer..."
		m.composer.SetHeight(1)
	} else {
		m.composer.Blur()
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
				b.WriteString(approvalActiveStyle.Render(fmt.Sprintf("  \u276f %d. %s", i+1, opt)))
			} else {
				b.WriteString(approvalInactiveStyle.Render(fmt.Sprintf("    %d. %s", i+1, opt)))
			}
			b.WriteString("\n")
		}

		if m.askAllowText {
			b.WriteString(dimStyle.Render("  (or type a custom answer below)"))
			b.WriteString("\n")
			b.WriteString(m.composer.View())
			b.WriteString("\n")
		}
		b.WriteString(dimStyle.Render("  \u2191/\u2193 select \u00b7 Enter confirm \u00b7 Esc cancel"))
		b.WriteString("\n")
	} else {
		// Free-text only
		b.WriteString(dimStyle.Render("  (type your answer)"))
		b.WriteString("\n")
		b.WriteString(m.composer.View())
		b.WriteString("\n")
		b.WriteString(dimStyle.Render("  Enter confirm \u00b7 Esc cancel"))
		b.WriteString("\n")
	}

	return b.String()
}

// handleAskUserKey handles key events during ask-user.
func handleAskUserKey(m model, msg tea.KeyPressMsg) (tea.Model, tea.Cmd) {
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

	case "backspace":
		// Session picker: filter backspace
		if m.askRequestID == -1 && len(m.sessionPickerFilter) > 0 {
			runes := []rune(m.sessionPickerFilter)
			m.sessionPickerFilter = string(runes[:len(runes)-1])
			m.askCursor = 0
			m = applySessionPickerFilter(m)
			return m, nil
		}
		// Fall through to composer when in text mode
		if m.askAllowText || len(m.askOptions) == 0 {
			var cmd tea.Cmd
			m.composer, cmd = m.composer.Update(msg)
			return m, cmd
		}
		return m, nil

	case "enter":
		// Session picker mode: sentinel askRequestID == -1
		if m.askRequestID == -1 {
			return handleSessionPickerSelection(m, m.askCursor)
		}

		var answer string

		// If composer has text and allowText, use that
		if m.askAllowText || len(m.askOptions) == 0 {
			text := strings.TrimSpace(m.composer.Value())
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
		m.composer.SetValue("")
		m.composer.Placeholder = "Ask AutoCode\u2026"
		m.composer.SetHeight(composerMinH)
		m.composer.Focus()

		return m, tea.Println(dimStyle.Render(fmt.Sprintf("  \u2192 %s", answer)))

	case "escape", "esc", "ctrl+c":
		// Session picker mode: first Escape clears filter, then cancels
		if m.askRequestID == -1 {
			if m.sessionPickerFilter != "" && msg.String() != "ctrl+c" {
				m.sessionPickerFilter = ""
				m.askCursor = 0
				m = applySessionPickerFilter(m)
				return m, nil
			}
			m.sessionPickerEntries = nil
			m.sessionPickerFilter = ""
			m.stage = stageInput
			m.composer.SetValue("")
			m.composer.Placeholder = "Ask AutoCode\u2026"
			m.composer.SetHeight(composerMinH)
			m.composer.Focus()
			return m, tea.Println(dimStyle.Render("  \u2192 (cancelled)"))
		}

		// Default answer
		answer := ""
		if len(m.askOptions) > 0 {
			answer = m.askOptions[0]
		}
		if m.backend != nil {
			m.backend.SendResponse(m.askRequestID, AskUserResult{Answer: answer})
		}

		m.stage = stageStreaming
		m.composer.SetValue("")
		m.composer.Placeholder = "Ask AutoCode\u2026"
		m.composer.SetHeight(composerMinH)
		m.composer.Focus()

		return m, tea.Println(dimStyle.Render("  \u2192 (cancelled)"))

	default:
		// Session picker: type-to-filter
		if m.askRequestID == -1 {
			if r := runeForFilter(msg); r != 0 {
				m.sessionPickerFilter += string(r)
				m.askCursor = 0
				m = applySessionPickerFilter(m)
				return m, nil
			}
			return m, nil
		}
		// Forward to composer if in text mode
		if m.askAllowText || len(m.askOptions) == 0 {
			var cmd tea.Cmd
			m.composer, cmd = m.composer.Update(msg)
			return m, cmd
		}
	}

	return m, nil
}
