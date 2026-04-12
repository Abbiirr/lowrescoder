package main

import (
	"encoding/json"
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
)

// enterModelPicker transitions to the model picker state with a list of
// models to choose from. The current active model is highlighted by default.
func enterModelPicker(m model, models []string, current string) model {
	m.stage = stageModelPicker
	m.modelPickerEntries = models
	m.modelPickerCurrent = current
	// Start cursor on the currently active model if present
	m.modelPickerCursor = 0
	for i, name := range models {
		if name == current {
			m.modelPickerCursor = i
			break
		}
	}
	m.composer.Blur()
	return m
}

// exitModelPicker returns to stageInput, clearing picker state.
func exitModelPicker(m model) model {
	m.stage = stageInput
	m.modelPickerEntries = nil
	m.modelPickerCursor = 0
	m.modelPickerCurrent = ""
	m.composer.Focus()
	return m
}

// renderModelPicker renders the model picker UI.
func renderModelPicker(m model) string {
	var b strings.Builder

	b.WriteString(welcomeStyle.Render("Select a model:"))
	b.WriteString("\n")

	// Cap at 10 visible lines around the cursor
	const windowSize = 10
	start := 0
	end := len(m.modelPickerEntries)
	if end > windowSize {
		// Center the cursor in the window when possible
		start = m.modelPickerCursor - windowSize/2
		if start < 0 {
			start = 0
		}
		end = start + windowSize
		if end > len(m.modelPickerEntries) {
			end = len(m.modelPickerEntries)
			start = end - windowSize
		}
	}

	if start > 0 {
		b.WriteString(dimStyle.Render(fmt.Sprintf("  [%d above]", start)))
		b.WriteString("\n")
	}

	for i := start; i < end; i++ {
		name := m.modelPickerEntries[i]
		marker := ""
		if name == m.modelPickerCurrent {
			marker = " (active)"
		}
		line := fmt.Sprintf("    %s%s", name, marker)
		if i == m.modelPickerCursor {
			line = approvalActiveStyle.Render(fmt.Sprintf("  \u276f %s%s", name, marker))
		} else {
			line = approvalInactiveStyle.Render(line)
		}
		b.WriteString(line)
		b.WriteString("\n")
	}

	if end < len(m.modelPickerEntries) {
		remaining := len(m.modelPickerEntries) - end
		b.WriteString(dimStyle.Render(fmt.Sprintf("  [%d below]", remaining)))
		b.WriteString("\n")
	}

	b.WriteString("\n")
	b.WriteString(dimStyle.Render("  Up/Down select \u00b7 Enter apply \u00b7 Esc cancel"))
	return b.String()
}

// handleModelPickerKey handles key events while the model picker is open.
func handleModelPickerKey(m model, msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	n := len(m.modelPickerEntries)
	if n == 0 {
		return exitModelPicker(m), nil
	}

	switch msg.String() {
	case "up", "k":
		m.modelPickerCursor--
		if m.modelPickerCursor < 0 {
			m.modelPickerCursor = n - 1
		}
		return m, nil

	case "down", "j":
		m.modelPickerCursor++
		if m.modelPickerCursor >= n {
			m.modelPickerCursor = 0
		}
		return m, nil

	case "enter":
		chosen := m.modelPickerEntries[m.modelPickerCursor]
		m = exitModelPicker(m)
		if m.backend != nil {
			m.backend.SendRequest("command", CommandParams{Cmd: "/model " + chosen})
		}
		return m, tea.Println(dimStyle.Render(fmt.Sprintf("  \u2192 model: %s", chosen)))

	case "escape", "esc", "ctrl+c":
		m = exitModelPicker(m)
		return m, tea.Println(dimStyle.Render("  \u2192 (cancelled)"))
	}

	return m, nil
}

// requestModelListCmd asks the Python backend for the list of available
// models; the result is delivered back via backendModelListMsg.
func requestModelListCmd(backend *Backend) tea.Cmd {
	if backend == nil {
		return func() tea.Msg {
			return backendErrorMsg{Message: "Backend not connected — /model picker unavailable"}
		}
	}
	return backend.SendRequestCmd(
		"model.list",
		struct{}{},
		func(result json.RawMessage, rpcErr *RPCError) tea.Msg {
			if rpcErr != nil {
				return backendErrorMsg{Message: "model.list failed: " + rpcErr.Message}
			}
			var payload struct {
				Models  []string `json:"models"`
				Current string   `json:"current"`
			}
			if err := json.Unmarshal(result, &payload); err != nil {
				return backendErrorMsg{Message: "failed to parse model.list: " + err.Error()}
			}
			return backendModelListMsg{Models: payload.Models, Current: payload.Current}
		},
	)
}
