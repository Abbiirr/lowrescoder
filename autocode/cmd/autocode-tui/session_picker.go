package main

import (
	"encoding/json"
	"fmt"
	"strings"

	tea "charm.land/bubbletea/v2"
)

// enterSessionPicker transitions the model to the session picker (reuses stageAskUser).
// Uses askRequestID == -1 as a sentinel to distinguish from real ask-user requests.
func enterSessionPicker(m model, msg backendSessionListMsg) model {
	m.sessionPickerEntries = msg.Sessions
	m.sessionPickerFilter = ""
	m.stage = stageAskUser
	m.askRequestID = -1
	m.askQuestion = "Select a session to resume:"
	m.askCursor = 0
	m.askAllowText = false
	m.askOptions = sessionPickerOptions(msg.Sessions)
	m.composer.Blur()
	return m
}

// sessionPickerOptions formats session entries for display, honoring the
// current filter. Returns the list of display strings that correspond
// one-to-one with the list returned by sessionPickerVisible.
func sessionPickerOptions(sessions []sessionEntry) []string {
	options := make([]string, len(sessions))
	for i, s := range sessions {
		options[i] = formatSessionOption(s)
	}
	return options
}

func formatSessionOption(s sessionEntry) string {
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
		return fmt.Sprintf("%s  %s  (%s)", idPrefix, title, s.Model)
	}
	return fmt.Sprintf("%s  %s", idPrefix, title)
}

// sessionPickerVisible returns the indices of sessionPickerEntries that
// match the current filter. A session matches if its formatted display
// string contains the filter as a case-insensitive substring.
func sessionPickerVisible(m model) []int {
	if len(m.sessionPickerEntries) == 0 {
		return nil
	}
	if m.sessionPickerFilter == "" {
		idx := make([]int, len(m.sessionPickerEntries))
		for i := range m.sessionPickerEntries {
			idx[i] = i
		}
		return idx
	}
	needle := strings.ToLower(m.sessionPickerFilter)
	out := make([]int, 0, len(m.sessionPickerEntries))
	for i, s := range m.sessionPickerEntries {
		display := strings.ToLower(formatSessionOption(s))
		if strings.Contains(display, needle) {
			out = append(out, i)
		}
	}
	return out
}

// applySessionPickerFilter rebuilds askOptions to reflect the filter
// state and clamps askCursor.
func applySessionPickerFilter(m model) model {
	visible := sessionPickerVisible(m)
	opts := make([]string, 0, len(visible))
	for _, idx := range visible {
		opts = append(opts, formatSessionOption(m.sessionPickerEntries[idx]))
	}
	m.askOptions = opts
	m.askCursor = clampCursorToVisible(m.askCursor, visible)
	return m
}

// handleSessionPickerSelection handles Enter on a session picker item.
// Sends session.resume to the backend and returns to stageInput.
// selectedVisibleIndex is an index into the currently-visible (filtered)
// list, not the raw sessionPickerEntries slice.
func handleSessionPickerSelection(m model, selectedVisibleIndex int) (model, tea.Cmd) {
	visible := sessionPickerVisible(m)
	if selectedVisibleIndex < 0 || selectedVisibleIndex >= len(visible) {
		m.stage = stageInput
		m.sessionPickerEntries = nil
		m.sessionPickerFilter = ""
		m.composer.Focus()
		return m, tea.Println(errorStyle.Render("Invalid session selection"))
	}

	sessionID := m.sessionPickerEntries[visible[selectedVisibleIndex]].ID

	// Clear picker state
	m.sessionPickerEntries = nil
	m.sessionPickerFilter = ""
	m.stage = stageInput
	m.composer.SetValue("")
	m.composer.Placeholder = "Ask AutoCode\u2026"
	m.composer.SetHeight(composerMinH)
	m.composer.Focus()

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
