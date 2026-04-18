package main

import (
	"encoding/json"
	"fmt"
	"strings"
	"unicode"

	tea "charm.land/bubbletea/v2"
)

// enterModelPicker transitions to the model picker state with a list of
// models to choose from. The current active model is highlighted by default.
func enterModelPicker(m model, models []string, current string) model {
	m.stage = stageModelPicker
	m.modelPickerEntries = models
	m.modelPickerCurrent = current
	m.modelPickerFilter = ""
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
	m.modelPickerFilter = ""
	m.composer.Focus()
	return m
}

// filteredPickerIndices returns the indices of entries whose names match
// the case-insensitive substring filter. Empty filter matches every entry.
// Returns indices into the original entries slice so the caller can map
// a visible cursor back to the real selection.
func filteredPickerIndices(entries []string, filter string) []int {
	if filter == "" {
		idx := make([]int, len(entries))
		for i := range entries {
			idx[i] = i
		}
		return idx
	}
	needle := strings.ToLower(filter)
	out := make([]int, 0, len(entries))
	for i, name := range entries {
		if strings.Contains(strings.ToLower(name), needle) {
			out = append(out, i)
		}
	}
	return out
}

// modelPickerVisible returns the list of entry indices currently visible
// after applying modelPickerFilter.
func modelPickerVisible(m model) []int {
	return filteredPickerIndices(m.modelPickerEntries, m.modelPickerFilter)
}

// clampCursorToVisible ensures cursor is a valid index in the visible slice.
func clampCursorToVisible(cursor int, visible []int) int {
	if len(visible) == 0 {
		return 0
	}
	if cursor < 0 {
		return 0
	}
	if cursor >= len(visible) {
		return len(visible) - 1
	}
	return cursor
}

// renderModelPicker renders the model picker UI.
func renderModelPicker(m model) string {
	var b strings.Builder

	header := "Select a model:"
	if m.modelPickerFilter != "" {
		header = fmt.Sprintf("Select a model:  [filter: %s]", m.modelPickerFilter)
	}
	b.WriteString(welcomeStyle.Render(header))
	b.WriteString("\n")

	visible := modelPickerVisible(m)
	if len(visible) == 0 {
		b.WriteString(dimStyle.Render("  (no matches — Backspace or Esc to clear)"))
		b.WriteString("\n\n")
		b.WriteString(dimStyle.Render("  Type to filter \u00b7 Up/Down select \u00b7 Enter apply \u00b7 Esc cancel"))
		return b.String()
	}

	// Cap at 10 visible lines around the cursor
	const windowSize = 10
	cursor := clampCursorToVisible(m.modelPickerCursor, visible)
	start := 0
	end := len(visible)
	if end > windowSize {
		start = cursor - windowSize/2
		if start < 0 {
			start = 0
		}
		end = start + windowSize
		if end > len(visible) {
			end = len(visible)
			start = end - windowSize
		}
	}

	if start > 0 {
		b.WriteString(dimStyle.Render(fmt.Sprintf("  [%d above]", start)))
		b.WriteString("\n")
	}

	for i := start; i < end; i++ {
		entryIdx := visible[i]
		name := m.modelPickerEntries[entryIdx]
		marker := ""
		if name == m.modelPickerCurrent {
			marker = " (active)"
		}
		line := fmt.Sprintf("    %s%s", name, marker)
		if i == cursor {
			line = approvalActiveStyle.Render(fmt.Sprintf("  \u276f %s%s", name, marker))
		} else {
			line = approvalInactiveStyle.Render(line)
		}
		b.WriteString(line)
		b.WriteString("\n")
	}

	if end < len(visible) {
		remaining := len(visible) - end
		b.WriteString(dimStyle.Render(fmt.Sprintf("  [%d below]", remaining)))
		b.WriteString("\n")
	}

	b.WriteString("\n")
	b.WriteString(dimStyle.Render("  Type to filter \u00b7 Up/Down select \u00b7 Enter apply \u00b7 Esc cancel"))
	return b.String()
}

// handleModelPickerKey handles key events while the model picker is open.
func handleModelPickerKey(m model, msg tea.KeyPressMsg) (tea.Model, tea.Cmd) {
	if len(m.modelPickerEntries) == 0 {
		return exitModelPicker(m), nil
	}

	switch msg.String() {
	case "up", "k":
		visible := modelPickerVisible(m)
		if len(visible) == 0 {
			return m, nil
		}
		m.modelPickerCursor = clampCursorToVisible(m.modelPickerCursor, visible)
		m.modelPickerCursor--
		if m.modelPickerCursor < 0 {
			m.modelPickerCursor = len(visible) - 1
		}
		return m, nil

	case "down", "j":
		visible := modelPickerVisible(m)
		if len(visible) == 0 {
			return m, nil
		}
		m.modelPickerCursor = clampCursorToVisible(m.modelPickerCursor, visible)
		m.modelPickerCursor++
		if m.modelPickerCursor >= len(visible) {
			m.modelPickerCursor = 0
		}
		return m, nil

	case "enter":
		visible := modelPickerVisible(m)
		if len(visible) == 0 {
			return m, nil
		}
		cursor := clampCursorToVisible(m.modelPickerCursor, visible)
		chosen := m.modelPickerEntries[visible[cursor]]
		m = exitModelPicker(m)
		if m.backend != nil {
			m.backend.SendRequest("command", CommandParams{Cmd: "/model " + chosen})
		}
		return m, tea.Println(dimStyle.Render(fmt.Sprintf("  \u2192 model: %s", chosen)))

	case "backspace":
		if len(m.modelPickerFilter) > 0 {
			runes := []rune(m.modelPickerFilter)
			m.modelPickerFilter = string(runes[:len(runes)-1])
			m.modelPickerCursor = 0
		}
		return m, nil

	case "escape", "esc":
		// Two-stroke: first Escape clears filter, second Escape exits.
		if m.modelPickerFilter != "" {
			m.modelPickerFilter = ""
			m.modelPickerCursor = 0
			return m, nil
		}
		m = exitModelPicker(m)
		return m, tea.Println(dimStyle.Render("  \u2192 (cancelled)"))

	case "ctrl+c":
		m = exitModelPicker(m)
		return m, tea.Println(dimStyle.Render("  \u2192 (cancelled)"))
	}

	// Type-to-filter: append printable non-control runes.
	if r := runeForFilter(msg); r != 0 {
		m.modelPickerFilter += string(r)
		m.modelPickerCursor = 0
	}
	return m, nil
}

// runeForFilter returns the single rune contributed by the key press if the
// key should be treated as filter input, else 0. Excludes control chars,
// digits are allowed (some model names contain digits like gpt-4).
func runeForFilter(msg tea.KeyPressMsg) rune {
	text := msg.Text
	if text == "" {
		return 0
	}
	// Reject modified keys (Ctrl, Alt, Super) except plain Shift via text case.
	if msg.Mod&(tea.ModCtrl|tea.ModAlt|tea.ModSuper) != 0 {
		return 0
	}
	runes := []rune(text)
	if len(runes) != 1 {
		return 0
	}
	r := runes[0]
	if unicode.IsControl(r) {
		return 0
	}
	return r
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
