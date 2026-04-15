package main

import (
	"strings"
	"testing"

	tea "charm.land/bubbletea/v2"
)

// --- enterSessionPicker tests ---

func TestEnterSessionPickerSetsAskUserStage(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	msg := backendSessionListMsg{
		Sessions: []sessionEntry{
			{ID: "aaaa1111-2222-3333-4444-555566667777", Title: "Test session", Model: "qwen3:8b", Provider: "ollama"},
		},
	}
	m = enterSessionPicker(m, msg)

	if m.stage != stageAskUser {
		t.Errorf("expected stageAskUser, got %d", m.stage)
	}
	if m.askRequestID != -1 {
		t.Errorf("expected sentinel askRequestID=-1, got %d", m.askRequestID)
	}
}

func TestEnterSessionPickerFormatsLabels(t *testing.T) {
	m := initialModel(nil)
	msg := backendSessionListMsg{
		Sessions: []sessionEntry{
			{ID: "72923c2f-abcd-1234-5678-999900001111", Title: "My project", Model: "qwen3:8b", Provider: "ollama"},
			{ID: "c2b875c7-xxxx-yyyy-zzzz-aabbccddeeff", Title: "Another session", Model: "gpt-4", Provider: "openrouter"},
		},
	}
	m = enterSessionPicker(m, msg)

	if len(m.askOptions) != 2 {
		t.Fatalf("expected 2 options, got %d", len(m.askOptions))
	}

	// Check ID prefix (first 8 chars)
	if !strings.HasPrefix(m.askOptions[0], "72923c2f") {
		t.Errorf("expected option to start with '72923c2f', got '%s'", m.askOptions[0])
	}

	// Check title is included
	if !strings.Contains(m.askOptions[0], "My project") {
		t.Errorf("expected 'My project' in label, got '%s'", m.askOptions[0])
	}

	// Check model is included in parens
	if !strings.Contains(m.askOptions[0], "(qwen3:8b)") {
		t.Errorf("expected '(qwen3:8b)' in label, got '%s'", m.askOptions[0])
	}

	// Check second option uses its own ID and model
	if !strings.HasPrefix(m.askOptions[1], "c2b875c7") {
		t.Errorf("expected second option to start with 'c2b875c7', got '%s'", m.askOptions[1])
	}
	if !strings.Contains(m.askOptions[1], "(gpt-4)") {
		t.Errorf("expected '(gpt-4)' in second label, got '%s'", m.askOptions[1])
	}
}

func TestEnterSessionPickerEmptyTitle(t *testing.T) {
	m := initialModel(nil)
	msg := backendSessionListMsg{
		Sessions: []sessionEntry{
			{ID: "abcdef12-xxxx-xxxx-xxxx-xxxxxxxxxxxx", Title: "", Model: "qwen3:8b"},
		},
	}
	m = enterSessionPicker(m, msg)

	if !strings.Contains(m.askOptions[0], "(untitled)") {
		t.Errorf("expected '(untitled)' for empty title, got '%s'", m.askOptions[0])
	}
}

func TestEnterSessionPickerLongTitle(t *testing.T) {
	m := initialModel(nil)
	longTitle := strings.Repeat("A", 50) // 50 chars, exceeds 40
	msg := backendSessionListMsg{
		Sessions: []sessionEntry{
			{ID: "abcdef12-xxxx-xxxx-xxxx-xxxxxxxxxxxx", Title: longTitle, Model: "m"},
		},
	}
	m = enterSessionPicker(m, msg)

	// Title should be truncated: first 37 chars + "..."
	if strings.Contains(m.askOptions[0], longTitle) {
		t.Errorf("expected long title to be truncated, but full title found in '%s'", m.askOptions[0])
	}
	if !strings.Contains(m.askOptions[0], "...") {
		t.Errorf("expected '...' truncation indicator in '%s'", m.askOptions[0])
	}
	// Verify truncated part is correct (first 37 chars of title)
	expectedTitlePart := longTitle[:37]
	if !strings.Contains(m.askOptions[0], expectedTitlePart) {
		t.Errorf("expected first 37 chars of title in label, got '%s'", m.askOptions[0])
	}
}

func TestEnterSessionPickerNoModel(t *testing.T) {
	m := initialModel(nil)
	msg := backendSessionListMsg{
		Sessions: []sessionEntry{
			{ID: "abcdef12-xxxx-xxxx-xxxx-xxxxxxxxxxxx", Title: "test", Model: ""},
		},
	}
	m = enterSessionPicker(m, msg)

	// No model → no parenthesized model suffix
	if strings.Contains(m.askOptions[0], "(") {
		t.Errorf("expected no model in parens when model empty, got '%s'", m.askOptions[0])
	}
}

func TestEnterSessionPickerBlursInput(t *testing.T) {
	m := initialModel(nil)
	m.composer.Focus()

	msg := backendSessionListMsg{
		Sessions: []sessionEntry{
			{ID: "aaaa1111", Title: "test", Model: "m"},
		},
	}
	m = enterSessionPicker(m, msg)

	if m.composer.Focused() {
		t.Error("expected composer blurred in session picker mode")
	}
}

func TestEnterSessionPickerStoresEntries(t *testing.T) {
	m := initialModel(nil)
	entries := []sessionEntry{
		{ID: "id1", Title: "s1", Model: "m1", Provider: "p1"},
		{ID: "id2", Title: "s2", Model: "m2", Provider: "p2"},
		{ID: "id3", Title: "s3", Model: "m3", Provider: "p3"},
	}
	msg := backendSessionListMsg{Sessions: entries}
	m = enterSessionPicker(m, msg)

	if len(m.sessionPickerEntries) != 3 {
		t.Fatalf("expected 3 session picker entries, got %d", len(m.sessionPickerEntries))
	}
	// Verify entries are stored with full IDs (not truncated)
	if m.sessionPickerEntries[0].ID != "id1" {
		t.Errorf("expected full ID 'id1', got '%s'", m.sessionPickerEntries[0].ID)
	}
	if m.sessionPickerEntries[2].Provider != "p3" {
		t.Errorf("expected provider 'p3', got '%s'", m.sessionPickerEntries[2].Provider)
	}
}

func TestEnterSessionPickerSetsQuestion(t *testing.T) {
	m := initialModel(nil)
	msg := backendSessionListMsg{
		Sessions: []sessionEntry{{ID: "x", Title: "t"}},
	}
	m = enterSessionPicker(m, msg)

	if m.askQuestion != "Select a session to resume:" {
		t.Errorf("expected question set, got '%s'", m.askQuestion)
	}
}

func TestEnterSessionPickerCursorAtZero(t *testing.T) {
	m := initialModel(nil)
	m.askCursor = 5 // was at some other position
	msg := backendSessionListMsg{
		Sessions: []sessionEntry{
			{ID: "a", Title: "1"},
			{ID: "b", Title: "2"},
		},
	}
	m = enterSessionPicker(m, msg)

	if m.askCursor != 0 {
		t.Errorf("expected cursor reset to 0, got %d", m.askCursor)
	}
}

func TestEnterSessionPickerShortID(t *testing.T) {
	// IDs shorter than 8 chars should not crash
	m := initialModel(nil)
	msg := backendSessionListMsg{
		Sessions: []sessionEntry{
			{ID: "abc", Title: "short id", Model: "m"},
		},
	}
	m = enterSessionPicker(m, msg)

	if !strings.HasPrefix(m.askOptions[0], "abc") {
		t.Errorf("expected label to start with short ID 'abc', got '%s'", m.askOptions[0])
	}
}

func TestEnterSessionPickerDisallowsText(t *testing.T) {
	m := initialModel(nil)
	msg := backendSessionListMsg{
		Sessions: []sessionEntry{{ID: "x", Title: "t"}},
	}
	m = enterSessionPicker(m, msg)

	if m.askAllowText {
		t.Error("expected askAllowText=false for session picker")
	}
}

// --- Arrow navigation through ask-user handler ---

func TestSessionPickerArrowNavigation(t *testing.T) {
	m := initialModel(nil)
	msg := backendSessionListMsg{
		Sessions: []sessionEntry{
			{ID: "a", Title: "first"},
			{ID: "b", Title: "second"},
			{ID: "c", Title: "third"},
		},
	}
	m = enterSessionPicker(m, msg)

	// Down arrow
	updated, _ := handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyDown}))
	m = updated.(model)
	if m.askCursor != 1 {
		t.Errorf("expected cursor=1 after down, got %d", m.askCursor)
	}

	// Down again
	updated, _ = handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyDown}))
	m = updated.(model)
	if m.askCursor != 2 {
		t.Errorf("expected cursor=2 after second down, got %d", m.askCursor)
	}

	// Down wraps to 0
	updated, _ = handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyDown}))
	m = updated.(model)
	if m.askCursor != 0 {
		t.Errorf("expected cursor=0 after wrap, got %d", m.askCursor)
	}

	// Up wraps to last
	updated, _ = handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyUp}))
	m = updated.(model)
	if m.askCursor != 2 {
		t.Errorf("expected cursor=2 after up wrap, got %d", m.askCursor)
	}
}

// --- Enter selection ---

func TestSessionPickerEnterSelectsSession(t *testing.T) {
	b := NewBackend()
	m := initialModel(b)
	entries := []sessionEntry{
		{ID: "full-uuid-1111-2222-3333-444455556666", Title: "First", Model: "qwen3:8b"},
		{ID: "full-uuid-aaaa-bbbb-cccc-ddddeeeeffff", Title: "Second", Model: "gpt-4"},
	}
	msg := backendSessionListMsg{Sessions: entries}
	m = enterSessionPicker(m, msg)
	m.askCursor = 1 // Select "Second"

	updated, cmd := handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	// Should return to stageInput
	if um.stage != stageInput {
		t.Errorf("expected stageInput after selection, got %d", um.stage)
	}
	// composer should be focused
	if !um.composer.Focused() {
		t.Error("expected composer focused after selection")
	}
	// sessionPickerEntries should be cleared
	if um.sessionPickerEntries != nil {
		t.Error("expected sessionPickerEntries nil after selection")
	}
	// Should have sent session.resume to backend (check writeCh)
	select {
	case data := <-b.writeCh:
		s := string(data)
		if !strings.Contains(s, "session.resume") {
			t.Errorf("expected session.resume in sent data, got %s", s)
		}
		if !strings.Contains(s, "full-uuid-aaaa-bbbb-cccc-ddddeeeeffff") {
			t.Errorf("expected full session ID in data, got %s", s)
		}
	default:
		t.Error("expected session.resume message in writeCh")
	}
	// Should return a Println cmd
	if cmd == nil {
		t.Error("expected Println command for confirmation message")
	}
}

func TestSessionPickerEnterFirstItem(t *testing.T) {
	b := NewBackend()
	m := initialModel(b)
	entries := []sessionEntry{
		{ID: "first-id-1234", Title: "First", Model: "m"},
		{ID: "second-id-5678", Title: "Second", Model: "m"},
	}
	msg := backendSessionListMsg{Sessions: entries}
	m = enterSessionPicker(m, msg)
	m.askCursor = 0 // Default first item

	updated, _ := handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	if um.stage != stageInput {
		t.Errorf("expected stageInput, got %d", um.stage)
	}

	// Verify the correct session ID was sent
	select {
	case data := <-b.writeCh:
		s := string(data)
		if !strings.Contains(s, "first-id-1234") {
			t.Errorf("expected first-id-1234 in data, got %s", s)
		}
	default:
		t.Error("expected message in writeCh")
	}
}

// --- Escape/Cancel ---

func TestSessionPickerEscapeCancels(t *testing.T) {
	m := initialModel(nil)
	entries := []sessionEntry{
		{ID: "a", Title: "test"},
	}
	msg := backendSessionListMsg{Sessions: entries}
	m = enterSessionPicker(m, msg)

	updated, cmd := handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyEscape}))
	um := updated.(model)

	if um.stage != stageInput {
		t.Errorf("expected stageInput after escape, got %d", um.stage)
	}
	if um.sessionPickerEntries != nil {
		t.Error("expected sessionPickerEntries nil after escape")
	}
	if !um.composer.Focused() {
		t.Error("expected composer focused after escape")
	}
	if cmd == nil {
		t.Error("expected Println command for cancel message")
	}
}

func TestSessionPickerCtrlCCancels(t *testing.T) {
	m := initialModel(nil)
	entries := []sessionEntry{
		{ID: "a", Title: "test"},
	}
	msg := backendSessionListMsg{Sessions: entries}
	m = enterSessionPicker(m, msg)

	updated, _ := handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: 'c', Mod: tea.ModCtrl}))
	um := updated.(model)

	if um.stage != stageInput {
		t.Errorf("expected stageInput after Ctrl+C, got %d", um.stage)
	}
	if um.sessionPickerEntries != nil {
		t.Error("expected sessionPickerEntries nil after Ctrl+C")
	}
}

func TestSessionPickerDoesNotSendResponseToBackend(t *testing.T) {
	b := NewBackend()
	m := initialModel(b)
	entries := []sessionEntry{
		{ID: "a", Title: "test"},
	}
	msg := backendSessionListMsg{Sessions: entries}
	m = enterSessionPicker(m, msg)

	// Escape should NOT send a SendResponse to backend (which would be bad since
	// there's no real ask-user request ID to respond to)
	handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyEscape}))

	// No AskUserResult should be in writeCh — only the cancel message
	// Drain any messages and check none contain "answer"
	select {
	case data := <-b.writeCh:
		s := string(data)
		if strings.Contains(s, "answer") {
			t.Errorf("session picker escape should NOT send AskUserResult, but got %s", s)
		}
	default:
		// Good — no message sent at all
	}
}

func TestSessionPickerSelectionResetsState(t *testing.T) {
	m := initialModel(nil)
	entries := []sessionEntry{
		{ID: "a", Title: "test"},
	}
	msg := backendSessionListMsg{Sessions: entries}
	m = enterSessionPicker(m, msg)

	updated, _ := handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	if um.sessionPickerEntries != nil {
		t.Error("expected sessionPickerEntries cleared after selection")
	}
	if um.composer.Value() != "" {
		t.Error("expected composer cleared after selection")
	}
}

// --- View rendering ---

func TestSessionPickerViewRendersCorrectly(t *testing.T) {
	m := initialModel(nil)
	m.width = 80
	entries := []sessionEntry{
		{ID: "72923c2f-abcd-1234", Title: "My project", Model: "qwen3:8b"},
		{ID: "c2b875c7-efgh-5678", Title: "Hello world", Model: "gpt-4"},
	}
	msg := backendSessionListMsg{Sessions: entries}
	m = enterSessionPicker(m, msg)

	view := m.View().Content

	// Should show the question
	if !strings.Contains(view, "Select a session to resume") {
		t.Errorf("expected question in view, got:\n%s", view)
	}
	// Should show session entries (truncated IDs)
	if !strings.Contains(view, "72923c2f") {
		t.Errorf("expected first session ID prefix in view, got:\n%s", view)
	}
	if !strings.Contains(view, "My project") {
		t.Errorf("expected session title in view, got:\n%s", view)
	}
	if !strings.Contains(view, "c2b875c7") {
		t.Errorf("expected second session ID prefix in view, got:\n%s", view)
	}
}

// --- Edge case: invalid selection index ---

func TestSessionPickerInvalidIndex(t *testing.T) {
	m := initialModel(nil)
	entries := []sessionEntry{
		{ID: "a", Title: "test"},
	}
	m.sessionPickerEntries = entries
	m.askOptions = []string{"a  test"}

	// Try selecting beyond bounds
	um, cmd := handleSessionPickerSelection(m, 5)

	if um.stage != stageInput {
		t.Errorf("expected stageInput on invalid index, got %d", um.stage)
	}
	if um.sessionPickerEntries != nil {
		t.Error("expected sessionPickerEntries cleared on invalid index")
	}
	if cmd == nil {
		t.Error("expected error message command on invalid index")
	}
}

func TestSessionPickerNegativeIndex(t *testing.T) {
	m := initialModel(nil)
	m.sessionPickerEntries = []sessionEntry{{ID: "a", Title: "t"}}
	m.askOptions = []string{"a  t"}

	um, cmd := handleSessionPickerSelection(m, -1)

	if um.stage != stageInput {
		t.Errorf("expected stageInput on negative index, got %d", um.stage)
	}
	if cmd == nil {
		t.Error("expected error command on negative index")
	}
}

// --- Multiple sessions with same title ---

func TestSessionPickerDuplicateTitles(t *testing.T) {
	m := initialModel(nil)
	entries := []sessionEntry{
		{ID: "aaaa1111", Title: "hello", Model: "m1"},
		{ID: "bbbb2222", Title: "hello", Model: "m2"},
	}
	msg := backendSessionListMsg{Sessions: entries}
	m = enterSessionPicker(m, msg)

	// Both labels should exist and be distinguishable by ID prefix
	if len(m.askOptions) != 2 {
		t.Fatalf("expected 2 options, got %d", len(m.askOptions))
	}
	if m.askOptions[0] == m.askOptions[1] {
		t.Error("expected different labels for sessions with same title but different IDs")
	}
	if !strings.Contains(m.askOptions[0], "aaaa1111") {
		t.Errorf("expected first ID prefix in first option, got '%s'", m.askOptions[0])
	}
	if !strings.Contains(m.askOptions[1], "bbbb2222") {
		t.Errorf("expected second ID prefix in second option, got '%s'", m.askOptions[1])
	}
}

// --- Verify picker state doesn't leak into regular ask-user ---

func TestRegularAskUserNotAffectedBySentinel(t *testing.T) {
	// After using session picker and returning to stageInput,
	// a real ask-user request should work normally
	m := initialModel(nil)

	// Enter and exit session picker
	entries := []sessionEntry{{ID: "a", Title: "test"}}
	m = enterSessionPicker(m, backendSessionListMsg{Sessions: entries})
	updated, _ := handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyEscape}))
	m = updated.(model)

	// Now simulate a real ask-user request
	m = enterAskUser(m, backendAskUserRequestMsg{
		RequestID: 42,
		Question:  "Real question?",
		Options:   []string{"Yes", "No"},
	})

	if m.askRequestID != 42 {
		t.Errorf("expected real askRequestID=42, got %d", m.askRequestID)
	}
	if m.stage != stageAskUser {
		t.Errorf("expected stageAskUser, got %d", m.stage)
	}
	if m.sessionPickerEntries != nil {
		t.Error("expected sessionPickerEntries nil for regular ask-user")
	}
}

// --- Verify handleSessionPickerSelection sends FULL ID, not truncated ---

func TestSessionPickerSendsFullSessionID(t *testing.T) {
	b := NewBackend()
	m := initialModel(b)
	fullID := "72923c2f-abcd-1234-5678-999900001111"
	entries := []sessionEntry{
		{ID: fullID, Title: "test", Model: "m"},
	}
	msg := backendSessionListMsg{Sessions: entries}
	m = enterSessionPicker(m, msg)

	handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))

	select {
	case data := <-b.writeCh:
		s := string(data)
		// Must contain the FULL UUID, not just "72923c2f"
		if !strings.Contains(s, fullID) {
			t.Errorf("expected full session ID '%s' in request, got %s", fullID, s)
		}
	default:
		t.Error("expected session.resume message")
	}
}
