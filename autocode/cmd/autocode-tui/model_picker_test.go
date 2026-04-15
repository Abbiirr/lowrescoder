package main

import (
	"strings"
	"testing"

	tea "charm.land/bubbletea/v2"
)

// --- Slash-menu cursor navigation (Entry 1067 acceptance slice) ---

func TestSlashMenuUpArrowMovesCursor(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.completions = []string{"/help", "/hello", "/history"}
	m.completionCursor = 1

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyUp}))
	um := updated.(model)
	if um.completionCursor != 0 {
		t.Errorf("expected cursor=0 after Up from 1, got %d", um.completionCursor)
	}
}

func TestSlashMenuUpArrowWrapsFromTop(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.completions = []string{"/help", "/hello", "/history"}
	m.completionCursor = 0

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyUp}))
	um := updated.(model)
	if um.completionCursor != 2 {
		t.Errorf("expected cursor=2 (wrap to bottom), got %d", um.completionCursor)
	}
}

func TestSlashMenuDownArrowMovesCursor(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.completions = []string{"/help", "/hello", "/history"}
	m.completionCursor = 0

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyDown}))
	um := updated.(model)
	if um.completionCursor != 1 {
		t.Errorf("expected cursor=1 after Down from 0, got %d", um.completionCursor)
	}
}

func TestSlashMenuDownArrowWrapsFromBottom(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.completions = []string{"/help", "/hello", "/history"}
	m.completionCursor = 2

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyDown}))
	um := updated.(model)
	if um.completionCursor != 0 {
		t.Errorf("expected cursor=0 (wrap to top), got %d", um.completionCursor)
	}
}

func TestSlashMenuEnterAcceptsHighlighted(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.completions = []string{"/help", "/hello", "/history"}
	m.completionCursor = 1 // /hello

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)
	if um.composer.Value() != "/hello" {
		t.Errorf("expected Enter to accept /hello, composer=%q", um.composer.Value())
	}
	if um.completions != nil {
		t.Error("expected completions cleared after Enter accept")
	}
	if um.completionCursor != 0 {
		t.Error("expected completionCursor reset after Enter accept")
	}
}

func TestSlashMenuTabAcceptsHighlighted(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.completions = []string{"/help", "/hello", "/history"}
	m.completionCursor = 2 // /history

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyTab}))
	um := updated.(model)
	if um.composer.Value() != "/history" {
		t.Errorf("expected Tab to accept /history, composer=%q", um.composer.Value())
	}
}

func TestSlashMenuEscapeClosesMenu(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.completions = []string{"/help", "/hello", "/history"}
	m.completionCursor = 1

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEscape}))
	um := updated.(model)
	if um.completions != nil {
		t.Error("expected Escape to close the slash menu")
	}
	if um.completionCursor != 0 {
		t.Error("expected completionCursor reset after Escape")
	}
	if um.stage != stageInput {
		t.Errorf("expected to stay in stageInput after Escape, got %d", um.stage)
	}
}

// --- Model picker state (Entry 1067 acceptance slice) ---

func TestEnterModelPickerSetsStage(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	result := enterModelPicker(m, []string{"gpt-4", "claude-3", "tools"}, "tools")
	if result.stage != stageModelPicker {
		t.Errorf("expected stageModelPicker, got %d", result.stage)
	}
	if len(result.modelPickerEntries) != 3 {
		t.Errorf("expected 3 model entries, got %d", len(result.modelPickerEntries))
	}
	// Cursor should start on the active model (tools = index 2)
	if result.modelPickerCursor != 2 {
		t.Errorf("expected cursor on active model (index 2), got %d", result.modelPickerCursor)
	}
	if result.modelPickerCurrent != "tools" {
		t.Errorf("expected current=tools, got %s", result.modelPickerCurrent)
	}
}

func TestEnterModelPickerActiveNotInListDefaultsZero(t *testing.T) {
	m := initialModel(nil)
	result := enterModelPicker(m, []string{"gpt-4", "claude-3"}, "not-present")
	if result.modelPickerCursor != 0 {
		t.Errorf("expected cursor=0 when active model is not in list, got %d", result.modelPickerCursor)
	}
}

func TestModelPickerUpArrowMovesCursor(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageModelPicker
	m.modelPickerEntries = []string{"a", "b", "c"}
	m.modelPickerCursor = 1

	updated, _ := handleModelPickerKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyUp}))
	um := updated.(model)
	if um.modelPickerCursor != 0 {
		t.Errorf("expected cursor=0 after Up from 1, got %d", um.modelPickerCursor)
	}
}

func TestModelPickerUpArrowWraps(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageModelPicker
	m.modelPickerEntries = []string{"a", "b", "c"}
	m.modelPickerCursor = 0

	updated, _ := handleModelPickerKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyUp}))
	um := updated.(model)
	if um.modelPickerCursor != 2 {
		t.Errorf("expected cursor=2 (wrap), got %d", um.modelPickerCursor)
	}
}

func TestModelPickerDownArrowMovesCursor(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageModelPicker
	m.modelPickerEntries = []string{"a", "b", "c"}
	m.modelPickerCursor = 0

	updated, _ := handleModelPickerKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyDown}))
	um := updated.(model)
	if um.modelPickerCursor != 1 {
		t.Errorf("expected cursor=1 after Down from 0, got %d", um.modelPickerCursor)
	}
}

func TestModelPickerDownArrowWraps(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageModelPicker
	m.modelPickerEntries = []string{"a", "b", "c"}
	m.modelPickerCursor = 2

	updated, _ := handleModelPickerKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyDown}))
	um := updated.(model)
	if um.modelPickerCursor != 0 {
		t.Errorf("expected cursor=0 (wrap), got %d", um.modelPickerCursor)
	}
}

func TestModelPickerVimNavigation(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageModelPicker
	m.modelPickerEntries = []string{"a", "b", "c"}
	m.modelPickerCursor = 0

	// 'j' down
	updated, _ := handleModelPickerKey(m, tea.KeyPressMsg(tea.Key{Text: "j", Code: 'j'}))
	um := updated.(model)
	if um.modelPickerCursor != 1 {
		t.Errorf("expected j=down, cursor=1, got %d", um.modelPickerCursor)
	}

	// 'k' up
	updated2, _ := handleModelPickerKey(um, tea.KeyPressMsg(tea.Key{Text: "k", Code: 'k'}))
	um2 := updated2.(model)
	if um2.modelPickerCursor != 0 {
		t.Errorf("expected k=up, cursor=0, got %d", um2.modelPickerCursor)
	}
}

func TestModelPickerEnterAppliesHighlighted(t *testing.T) {
	b := NewBackend()
	m := initialModel(b)
	m.stage = stageModelPicker
	m.modelPickerEntries = []string{"gpt-4", "claude-3", "tools"}
	m.modelPickerCursor = 1 // claude-3

	updated, _ := handleModelPickerKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)
	if um.stage != stageInput {
		t.Errorf("expected return to stageInput after apply, got %d", um.stage)
	}
	if um.modelPickerEntries != nil {
		t.Error("expected picker entries cleared after apply")
	}

	// Backend should have received the /model command
	select {
	case data := <-b.writeCh:
		if !strings.Contains(string(data), "claude-3") {
			t.Errorf("expected /model claude-3 request sent to backend, got %s", data)
		}
	default:
		t.Error("expected /model request sent to backend on Enter")
	}
}

func TestModelPickerEscapeCancels(t *testing.T) {
	b := NewBackend()
	m := initialModel(b)
	m.stage = stageModelPicker
	m.modelPickerEntries = []string{"a", "b"}
	m.modelPickerCursor = 1

	updated, _ := handleModelPickerKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyEscape}))
	um := updated.(model)
	if um.stage != stageInput {
		t.Errorf("expected return to stageInput after Escape, got %d", um.stage)
	}
	if um.modelPickerEntries != nil {
		t.Error("expected picker entries cleared after Escape")
	}
	// No request should have been sent
	select {
	case <-b.writeCh:
		t.Error("expected NO backend request on Escape cancel")
	default:
		// ok
	}
}

func TestModelPickerCtrlCCancels(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageModelPicker
	m.modelPickerEntries = []string{"a", "b"}
	m.modelPickerCursor = 0

	updated, _ := handleModelPickerKey(m, tea.KeyPressMsg(tea.Key{Code: 'c', Mod: tea.ModCtrl}))
	um := updated.(model)
	if um.stage != stageInput {
		t.Errorf("expected return to stageInput after Ctrl+C, got %d", um.stage)
	}
}

func TestModelPickerEmptyListExits(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageModelPicker
	m.modelPickerEntries = nil

	// Any key with empty list should exit back to input
	updated, _ := handleModelPickerKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyUp}))
	um := updated.(model)
	if um.stage != stageInput {
		t.Errorf("expected exit to stageInput on empty list, got %d", um.stage)
	}
}

func TestModelPickerRenderIncludesActiveMarker(t *testing.T) {
	m := initialModel(nil)
	m.modelPickerEntries = []string{"gpt-4", "claude-3", "tools"}
	m.modelPickerCurrent = "tools"
	m.modelPickerCursor = 0 // cursor on gpt-4, NOT on active

	view := renderModelPicker(m)
	// Should contain the active marker somewhere
	if !strings.Contains(view, "(active)") {
		t.Errorf("expected (active) marker in view, got:\n%s", view)
	}
	// Cursor is on gpt-4 — that line should have ❯
	lines := strings.Split(view, "\n")
	foundCursor := false
	for _, line := range lines {
		if strings.Contains(line, "\u276f") && strings.Contains(line, "gpt-4") {
			foundCursor = true
			break
		}
	}
	if !foundCursor {
		t.Errorf("expected cursor ❯ on gpt-4, got view:\n%s", view)
	}
}

// --- Bare /model opens picker (not text dump) ---

func TestBareSlashModelOpensPicker(t *testing.T) {
	b := NewBackend()
	m := initialModel(b)
	m.stage = stageInput
	m.composer.SetValue("/model")

	// Enter should trigger model.list request, not /model text dump
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	// Composer should be cleared after the submit
	if um.composer.Value() != "" {
		t.Errorf("expected composer cleared, got %q", um.composer.Value())
	}

	// Backend should have received model.list request
	select {
	case data := <-b.writeCh:
		if !strings.Contains(string(data), "model.list") {
			t.Errorf("expected model.list request, got %s", data)
		}
	default:
		t.Error("expected model.list request sent to backend")
	}
}

func TestBareSlashMOpensModelPicker(t *testing.T) {
	// /m is an alias for /model — should also open the picker
	b := NewBackend()
	m := initialModel(b)
	m.stage = stageInput
	m.composer.SetValue("/m")

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	_ = updated.(model)

	select {
	case data := <-b.writeCh:
		if !strings.Contains(string(data), "model.list") {
			t.Errorf("expected model.list request for /m alias, got %s", data)
		}
	default:
		t.Error("expected model.list request for /m alias")
	}
}

// --- backendModelListMsg transitions to picker stage ---

func TestBackendModelListMsgEntersPicker(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, _ := m.Update(backendModelListMsg{
		Models:  []string{"gpt-4", "claude-3"},
		Current: "claude-3",
	})
	um := updated.(model)
	if um.stage != stageModelPicker {
		t.Errorf("expected stageModelPicker after model.list response, got %d", um.stage)
	}
	if um.modelPickerCurrent != "claude-3" {
		t.Errorf("expected current=claude-3, got %s", um.modelPickerCurrent)
	}
}

func TestBackendModelListMsgEmptySetsError(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, _ := m.Update(backendModelListMsg{Models: nil, Current: ""})
	um := updated.(model)
	if um.stage == stageModelPicker {
		t.Error("expected NOT to enter picker with empty model list")
	}
	if um.lastError == "" {
		t.Error("expected lastError set on empty model list")
	}
}

// --- C1 regression: model picker must NOT appear after a normal chat turn ---

// TestModelPickerDoesNotAppearAfterChatDone verifies the C1 regression:
// a normal backendDoneMsg (end of chat turn) must not open the model picker.
// Previously the picker could appear unsolicited, blocking every chat turn.
func TestModelPickerDoesNotAppearAfterChatDone(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.tokenBuf.WriteString("Hello!")
	m.streamBuf.WriteString("Hello!")

	updated, _ := m.Update(backendDoneMsg{TokensIn: 5, TokensOut: 10})
	um := updated.(model)

	if um.stage == stageModelPicker {
		t.Error("C1 regression: model picker must not open after a normal chat done event")
	}
	if um.stage != stageInput {
		t.Errorf("expected stageInput after done, got stage=%d", um.stage)
	}
}

// TestModelPickerDoesNotAppearAfterStatus verifies that on_status notifications
// (sent by the backend after model/provider changes) do not open the model picker.
func TestModelPickerDoesNotAppearAfterStatus(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, _ := m.Update(backendStatusMsg{Model: "tools", Provider: "openai", Mode: "suggest"})
	um := updated.(model)

	if um.stage == stageModelPicker {
		t.Error("C1 regression: model picker must not open on backendStatusMsg")
	}
}

// TestStartupTimeoutTransitionsToInput verifies that startupTimeoutMsg
// unblocks stageInit and transitions to stageInput even without backendStatusMsg.
func TestStartupTimeoutTransitionsToInput(t *testing.T) {
	m := initialModel(nil)
	// Starts in stageInit — simulates slow/missing backend
	if m.stage != stageInit {
		t.Fatalf("expected stageInit on init, got %d", m.stage)
	}

	updated, _ := m.Update(startupTimeoutMsg{})
	um := updated.(model)

	if um.stage != stageInput {
		t.Errorf("expected stageInput after startup timeout, got %d", um.stage)
	}
	if um.lastError == "" {
		t.Error("expected lastError set after startup timeout (backend not connected warning)")
	}
}

// TestStartupTimeoutNoopAfterBackendConnects verifies that startupTimeoutMsg
// arriving after the backend already connected does not override the connected state.
func TestStartupTimeoutNoopAfterBackendConnects(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput // already connected
	m.lastError = ""

	updated, _ := m.Update(startupTimeoutMsg{})
	um := updated.(model)

	// Should be a no-op since we're not in stageInit
	if um.stage != stageInput {
		t.Errorf("expected stageInput unchanged, got %d", um.stage)
	}
	// lastError should not be set if we were already connected
	if um.lastError != "" {
		t.Errorf("unexpected lastError after noop timeout: %s", um.lastError)
	}
}
