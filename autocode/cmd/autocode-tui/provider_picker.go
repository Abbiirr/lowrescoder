package main

import (
	"encoding/json"
	"fmt"
	"strings"

	tea "charm.land/bubbletea/v2"
)

// enterProviderPicker transitions to the provider picker state with the
// list of supported providers from the backend. Cursor starts on the
// active provider when present.
func enterProviderPicker(m model, providers []string, current string) model {
	m.stage = stageProviderPicker
	m.providerPickerEntries = providers
	m.providerPickerCurrent = current
	m.providerPickerFilter = ""
	m.providerPickerCursor = 0
	for i, name := range providers {
		if name == current {
			m.providerPickerCursor = i
			break
		}
	}
	m.composer.Blur()
	return m
}

// exitProviderPicker returns to stageInput, clearing picker state.
func exitProviderPicker(m model) model {
	m.stage = stageInput
	m.providerPickerEntries = nil
	m.providerPickerCursor = 0
	m.providerPickerCurrent = ""
	m.providerPickerFilter = ""
	m.composer.Focus()
	return m
}

// providerPickerVisible returns the indices into m.providerPickerEntries
// that match the current filter.
func providerPickerVisible(m model) []int {
	return filteredPickerIndices(m.providerPickerEntries, m.providerPickerFilter)
}

// renderProviderPicker renders the provider picker UI.
func renderProviderPicker(m model) string {
	var b strings.Builder

	header := "Select a provider:"
	if m.providerPickerFilter != "" {
		header = fmt.Sprintf("Select a provider:  [filter: %s]", m.providerPickerFilter)
	}
	b.WriteString(welcomeStyle.Render(header))
	b.WriteString("\n")

	visible := providerPickerVisible(m)
	if len(visible) == 0 {
		b.WriteString(dimStyle.Render("  (no matches — Backspace or Esc to clear)"))
		b.WriteString("\n\n")
		b.WriteString(dimStyle.Render("  Type to filter \u00b7 Up/Down select \u00b7 Enter apply \u00b7 Esc cancel"))
		return b.String()
	}

	cursor := clampCursorToVisible(m.providerPickerCursor, visible)
	for i, entryIdx := range visible {
		name := m.providerPickerEntries[entryIdx]
		marker := ""
		if name == m.providerPickerCurrent {
			marker = " (active)"
		}
		if i == cursor {
			b.WriteString(approvalActiveStyle.Render(fmt.Sprintf("  \u276f %s%s", name, marker)))
		} else {
			b.WriteString(approvalInactiveStyle.Render(fmt.Sprintf("    %s%s", name, marker)))
		}
		b.WriteString("\n")
	}

	b.WriteString("\n")
	b.WriteString(dimStyle.Render("  Type to filter \u00b7 Up/Down select \u00b7 Enter apply \u00b7 Esc cancel"))
	return b.String()
}

// handleProviderPickerKey handles key events while the provider picker is open.
func handleProviderPickerKey(m model, msg tea.KeyPressMsg) (tea.Model, tea.Cmd) {
	if len(m.providerPickerEntries) == 0 {
		return exitProviderPicker(m), nil
	}

	switch msg.String() {
	case "up", "k":
		visible := providerPickerVisible(m)
		if len(visible) == 0 {
			return m, nil
		}
		m.providerPickerCursor = clampCursorToVisible(m.providerPickerCursor, visible)
		m.providerPickerCursor--
		if m.providerPickerCursor < 0 {
			m.providerPickerCursor = len(visible) - 1
		}
		return m, nil

	case "down", "j":
		visible := providerPickerVisible(m)
		if len(visible) == 0 {
			return m, nil
		}
		m.providerPickerCursor = clampCursorToVisible(m.providerPickerCursor, visible)
		m.providerPickerCursor++
		if m.providerPickerCursor >= len(visible) {
			m.providerPickerCursor = 0
		}
		return m, nil

	case "enter":
		visible := providerPickerVisible(m)
		if len(visible) == 0 {
			return m, nil
		}
		cursor := clampCursorToVisible(m.providerPickerCursor, visible)
		chosen := m.providerPickerEntries[visible[cursor]]
		m = exitProviderPicker(m)
		if m.backend != nil {
			m.backend.SendRequest("command", CommandParams{Cmd: "/provider " + chosen})
		}
		return m, tea.Println(dimStyle.Render(fmt.Sprintf("  \u2192 provider: %s", chosen)))

	case "backspace":
		if len(m.providerPickerFilter) > 0 {
			runes := []rune(m.providerPickerFilter)
			m.providerPickerFilter = string(runes[:len(runes)-1])
			m.providerPickerCursor = 0
		}
		return m, nil

	case "escape", "esc":
		if m.providerPickerFilter != "" {
			m.providerPickerFilter = ""
			m.providerPickerCursor = 0
			return m, nil
		}
		m = exitProviderPicker(m)
		return m, tea.Println(dimStyle.Render("  \u2192 (cancelled)"))

	case "ctrl+c":
		m = exitProviderPicker(m)
		return m, tea.Println(dimStyle.Render("  \u2192 (cancelled)"))
	}

	if r := runeForFilter(msg); r != 0 {
		m.providerPickerFilter += string(r)
		m.providerPickerCursor = 0
	}
	return m, nil
}

// requestProviderListCmd asks the Python backend for the list of
// supported providers; the result is delivered back via
// backendProviderListMsg.
func requestProviderListCmd(backend *Backend) tea.Cmd {
	if backend == nil {
		return func() tea.Msg {
			return backendErrorMsg{Message: "Backend not connected — /provider picker unavailable"}
		}
	}
	return backend.SendRequestCmd(
		"provider.list",
		struct{}{},
		func(result json.RawMessage, rpcErr *RPCError) tea.Msg {
			if rpcErr != nil {
				return backendErrorMsg{Message: "provider.list failed: " + rpcErr.Message}
			}
			var payload struct {
				Providers []string `json:"providers"`
				Current   string   `json:"current"`
			}
			if err := json.Unmarshal(result, &payload); err != nil {
				return backendErrorMsg{Message: "failed to parse provider.list: " + err.Error()}
			}
			return backendProviderListMsg{Providers: payload.Providers, Current: payload.Current}
		},
	)
}
