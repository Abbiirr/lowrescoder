package main

import (
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"
)

// --- Provider picker state transitions ---

func TestEnterProviderPickerSetsStage(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	result := enterProviderPicker(m, []string{"ollama", "openrouter"}, "openrouter")
	if result.stage != stageProviderPicker {
		t.Errorf("expected stageProviderPicker, got %d", result.stage)
	}
	if len(result.providerPickerEntries) != 2 {
		t.Errorf("expected 2 entries, got %d", len(result.providerPickerEntries))
	}
	if result.providerPickerCursor != 1 {
		t.Errorf("expected cursor on active (index 1 = openrouter), got %d", result.providerPickerCursor)
	}
	if result.providerPickerCurrent != "openrouter" {
		t.Errorf("expected current=openrouter, got %s", result.providerPickerCurrent)
	}
}

func TestEnterProviderPickerActiveNotInListDefaultsZero(t *testing.T) {
	m := initialModel(nil)
	result := enterProviderPicker(m, []string{"ollama", "openrouter"}, "not-present")
	if result.providerPickerCursor != 0 {
		t.Errorf("expected cursor=0, got %d", result.providerPickerCursor)
	}
}

// --- Arrow navigation ---

func TestProviderPickerUpArrowMovesCursor(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageProviderPicker
	m.providerPickerEntries = []string{"ollama", "openrouter"}
	m.providerPickerCursor = 1

	updated, _ := handleProviderPickerKey(m, tea.KeyMsg{Type: tea.KeyUp})
	um := updated.(model)
	if um.providerPickerCursor != 0 {
		t.Errorf("expected cursor=0 after Up, got %d", um.providerPickerCursor)
	}
}

func TestProviderPickerUpArrowWraps(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageProviderPicker
	m.providerPickerEntries = []string{"ollama", "openrouter"}
	m.providerPickerCursor = 0

	updated, _ := handleProviderPickerKey(m, tea.KeyMsg{Type: tea.KeyUp})
	um := updated.(model)
	if um.providerPickerCursor != 1 {
		t.Errorf("expected cursor=1 (wrap), got %d", um.providerPickerCursor)
	}
}

func TestProviderPickerDownArrowMovesCursor(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageProviderPicker
	m.providerPickerEntries = []string{"ollama", "openrouter"}
	m.providerPickerCursor = 0

	updated, _ := handleProviderPickerKey(m, tea.KeyMsg{Type: tea.KeyDown})
	um := updated.(model)
	if um.providerPickerCursor != 1 {
		t.Errorf("expected cursor=1 after Down, got %d", um.providerPickerCursor)
	}
}

func TestProviderPickerDownArrowWraps(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageProviderPicker
	m.providerPickerEntries = []string{"ollama", "openrouter"}
	m.providerPickerCursor = 1

	updated, _ := handleProviderPickerKey(m, tea.KeyMsg{Type: tea.KeyDown})
	um := updated.(model)
	if um.providerPickerCursor != 0 {
		t.Errorf("expected cursor=0 (wrap), got %d", um.providerPickerCursor)
	}
}

func TestProviderPickerVimJkNavigation(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageProviderPicker
	m.providerPickerEntries = []string{"ollama", "openrouter"}
	m.providerPickerCursor = 0

	// j = down
	updated, _ := handleProviderPickerKey(m, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'j'}})
	um := updated.(model)
	if um.providerPickerCursor != 1 {
		t.Errorf("expected j=down cursor=1, got %d", um.providerPickerCursor)
	}

	// k = up
	updated2, _ := handleProviderPickerKey(um, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'k'}})
	um2 := updated2.(model)
	if um2.providerPickerCursor != 0 {
		t.Errorf("expected k=up cursor=0, got %d", um2.providerPickerCursor)
	}
}

// --- Enter / Escape ---

func TestProviderPickerEnterAppliesHighlighted(t *testing.T) {
	b := NewBackend()
	m := initialModel(b)
	m.stage = stageProviderPicker
	m.providerPickerEntries = []string{"ollama", "openrouter"}
	m.providerPickerCursor = 1 // openrouter

	updated, _ := handleProviderPickerKey(m, tea.KeyMsg{Type: tea.KeyEnter})
	um := updated.(model)
	if um.stage != stageInput {
		t.Errorf("expected return to stageInput, got %d", um.stage)
	}
	if um.providerPickerEntries != nil {
		t.Error("expected entries cleared after apply")
	}

	// Backend should have received the /provider command
	select {
	case data := <-b.writeCh:
		if !strings.Contains(string(data), "openrouter") {
			t.Errorf("expected /provider openrouter request, got %s", data)
		}
	default:
		t.Error("expected /provider request sent to backend on Enter")
	}
}

func TestProviderPickerEscapeCancels(t *testing.T) {
	b := NewBackend()
	m := initialModel(b)
	m.stage = stageProviderPicker
	m.providerPickerEntries = []string{"ollama", "openrouter"}
	m.providerPickerCursor = 1

	updated, _ := handleProviderPickerKey(m, tea.KeyMsg{Type: tea.KeyEsc})
	um := updated.(model)
	if um.stage != stageInput {
		t.Errorf("expected return to stageInput after Escape, got %d", um.stage)
	}
	if um.providerPickerEntries != nil {
		t.Error("expected entries cleared after Escape")
	}
	// No request should have been sent
	select {
	case <-b.writeCh:
		t.Error("expected NO backend request on Escape cancel")
	default:
		// ok
	}
}

func TestProviderPickerCtrlCCancels(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageProviderPicker
	m.providerPickerEntries = []string{"ollama", "openrouter"}

	updated, _ := handleProviderPickerKey(m, tea.KeyMsg{Type: tea.KeyCtrlC})
	um := updated.(model)
	if um.stage != stageInput {
		t.Errorf("expected return to stageInput after Ctrl+C, got %d", um.stage)
	}
}

func TestProviderPickerEmptyListExits(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageProviderPicker
	m.providerPickerEntries = nil

	updated, _ := handleProviderPickerKey(m, tea.KeyMsg{Type: tea.KeyUp})
	um := updated.(model)
	if um.stage != stageInput {
		t.Errorf("expected exit to stageInput on empty list, got %d", um.stage)
	}
}

// --- Render ---

func TestProviderPickerRenderIncludesActiveMarker(t *testing.T) {
	m := initialModel(nil)
	m.providerPickerEntries = []string{"ollama", "openrouter"}
	m.providerPickerCurrent = "openrouter"
	m.providerPickerCursor = 0 // cursor on ollama, NOT on active

	view := renderProviderPicker(m)
	if !strings.Contains(view, "(active)") {
		t.Errorf("expected (active) marker, got:\n%s", view)
	}
	// Cursor should be on ollama (❯ glyph)
	foundCursor := false
	for _, line := range strings.Split(view, "\n") {
		if strings.Contains(line, "\u276f") && strings.Contains(line, "ollama") {
			foundCursor = true
			break
		}
	}
	if !foundCursor {
		t.Errorf("expected cursor ❯ on ollama, got:\n%s", view)
	}
}

// --- Bare /provider opens picker via RPC ---

func TestBareSlashProviderOpensPicker(t *testing.T) {
	b := NewBackend()
	m := initialModel(b)
	m.stage = stageInput
	m.composer.SetValue("/provider")

	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	um := updated.(model)
	// Composer cleared
	if um.composer.Value() != "" {
		t.Errorf("expected composer cleared, got %q", um.composer.Value())
	}

	// Backend should have received provider.list request
	select {
	case data := <-b.writeCh:
		if !strings.Contains(string(data), "provider.list") {
			t.Errorf("expected provider.list request, got %s", data)
		}
	default:
		t.Error("expected provider.list request on bare /provider")
	}
}

// --- backendProviderListMsg transition ---

func TestBackendProviderListMsgEntersPicker(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, _ := m.Update(backendProviderListMsg{
		Providers: []string{"ollama", "openrouter"},
		Current:   "openrouter",
	})
	um := updated.(model)
	if um.stage != stageProviderPicker {
		t.Errorf("expected stageProviderPicker, got %d", um.stage)
	}
	if um.providerPickerCurrent != "openrouter" {
		t.Errorf("expected current=openrouter, got %s", um.providerPickerCurrent)
	}
}

func TestBackendProviderListMsgEmptySetsError(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, _ := m.Update(backendProviderListMsg{Providers: nil, Current: ""})
	um := updated.(model)
	if um.stage == stageProviderPicker {
		t.Error("expected NOT to enter picker with empty provider list")
	}
	if um.lastError == "" {
		t.Error("expected lastError set")
	}
}
