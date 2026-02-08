package main

import (
	"encoding/json"
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
)

// enterSessionPicker transitions the model to the session picker (reuses stageAskUser).
// Uses askRequestID == -1 as a sentinel to distinguish from real ask-user requests.
func enterSessionPicker(m model, msg backendSessionListMsg) model {
	m.sessionPickerEntries = msg.Sessions
	m.stage = stageAskUser
	m.askRequestID = -1
	m.askQuestion = "Select a session to resume:"
	m.askCursor = 0
	m.askAllowText = false

	// Format labels: "id[:8]  title  (model)"
	options := make([]string, len(msg.Sessions))
	for i, s := range msg.Sessions {
		idPrefix := s.ID
		if len(idPrefix) > 8 {
			idPrefix = idPrefix[:8]
		}

		title := s.Title
		if title == "" {
			title = "(untitled)"
		}
		if len(title) > 40 {
			title = title[:37] + "..."
		}

		if s.Model != "" {
			options[i] = fmt.Sprintf("%s  %s  (%s)", idPrefix, title, s.Model)
		} else {
			options[i] = fmt.Sprintf("%s  %s", idPrefix, title)
		}
	}
	m.askOptions = options

	m.textInput.Blur()

	return m
}

// handleSessionPickerSelection handles Enter on a session picker item.
// Sends session.resume to the backend and returns to stageInput.
func handleSessionPickerSelection(m model, selectedIndex int) (model, tea.Cmd) {
	if selectedIndex < 0 || selectedIndex >= len(m.sessionPickerEntries) {
		m.stage = stageInput
		m.sessionPickerEntries = nil
		m.textInput.Focus()
		return m, tea.Println(errorStyle.Render("Invalid session selection"))
	}

	sessionID := m.sessionPickerEntries[selectedIndex].ID

	// Clear picker state
	m.sessionPickerEntries = nil
	m.stage = stageInput
	m.textInput.SetValue("")
	m.textInput.Placeholder = "Type a message..."
	m.textInput.Focus()

	// Send session.resume to backend
	if m.backend != nil {
		return m, sessionResumeCmd(m.backend, sessionID)
	}

	return m, tea.Println(dimStyle.Render("  Backend not connected — cannot resume session"))
}

// sessionResumeCmd sends session.resume and maps the response to a user-facing message.
func sessionResumeCmd(backend *Backend, sessionID string) tea.Cmd {
	return backend.SendRequestCmd("session.resume", SessionResumeParams{SessionID: sessionID}, func(result json.RawMessage, rpcErr *RPCError) tea.Msg {
		if rpcErr != nil {
			return backendErrorMsg{Message: "session.resume failed: " + rpcErr.Message}
		}

		var resumeResult struct {
			SessionID string `json:"session_id"`
			Title     string `json:"title"`
			Error     string `json:"error"`
		}
		if err := json.Unmarshal(result, &resumeResult); err != nil {
			return backendErrorMsg{Message: "failed to parse session.resume result: " + err.Error()}
		}
		if resumeResult.Error != "" {
			return backendErrorMsg{Message: resumeResult.Error}
		}
		if resumeResult.SessionID == "" {
			return backendErrorMsg{Message: "session.resume returned empty session_id"}
		}

		shortID := resumeResult.SessionID
		if len(shortID) > 8 {
			shortID = shortID[:8]
		}

		title := strings.TrimSpace(resumeResult.Title)
		if title == "" {
			title = "(untitled)"
		}

		return backendTokenMsg{
			Text: dimStyle.Render(fmt.Sprintf("  Resumed session: %s  %s\n", shortID, title)),
		}
	})
}
