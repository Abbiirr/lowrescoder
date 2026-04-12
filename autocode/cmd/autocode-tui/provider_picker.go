package main

import (
	"encoding/json"
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
)

// enterProviderPicker transitions to the provider picker state with the
// list of supported providers from the backend. Cursor starts on the
// active provider when present.
func enterProviderPicker(m model, providers []string, current string) model {
	m.stage = stageProviderPicker
	m.providerPickerEntries = providers
	m.providerPickerCurrent = current
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
	m.composer.Focus()
	return m
}

// renderProviderPicker renders the provider picker UI.
func renderProviderPicker(m model) string {
	var b strings.Builder

	b.WriteString(welcomeStyle.Render("Select a provider:"))
	b.WriteString("\n")

	for i, name := range m.providerPickerEntries {
		marker := ""
		if name == m.providerPickerCurrent {
			marker = " (active)"
		}
		if i == m.providerPickerCursor {
			b.WriteString(approvalActiveStyle.Render(fmt.Sprintf("  \u276f %s%s", name, marker)))
		} else {
			b.WriteString(approvalInactiveStyle.Render(fmt.Sprintf("    %s%s", name, marker)))
		}
		b.WriteString("\n")
	}

	b.WriteString("\n")
	b.WriteString(dimStyle.Render("  Up/Down select \u00b7 Enter apply \u00b7 Esc cancel"))
	return b.String()
}

// handleProviderPickerKey handles key events while the provider picker is open.
func handleProviderPickerKey(m model, msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	n := len(m.providerPickerEntries)
	if n == 0 {
		return exitProviderPicker(m), nil
	}

	switch msg.String() {
	case "up", "k":
		m.providerPickerCursor--
		if m.providerPickerCursor < 0 {
			m.providerPickerCursor = n - 1
		}
		return m, nil

	case "down", "j":
		m.providerPickerCursor++
		if m.providerPickerCursor >= n {
			m.providerPickerCursor = 0
		}
		return m, nil

	case "enter":
		chosen := m.providerPickerEntries[m.providerPickerCursor]
		m = exitProviderPicker(m)
		if m.backend != nil {
			m.backend.SendRequest("command", CommandParams{Cmd: "/provider " + chosen})
		}
		return m, tea.Println(dimStyle.Render(fmt.Sprintf("  \u2192 provider: %s", chosen)))

	case "escape", "esc", "ctrl+c":
		m = exitProviderPicker(m)
		return m, tea.Println(dimStyle.Render("  \u2192 (cancelled)"))
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
