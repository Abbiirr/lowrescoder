package main

import (
	"strings"
	"testing"

	tea "charm.land/bubbletea/v2"
)

func TestEnterAskUserWithOptions(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.composer.Focus()

	result := enterAskUser(m, backendAskUserRequestMsg{
		RequestID: 100,
		Question:  "Pick one",
		Options:   []string{"A", "B", "C"},
		AllowText: false,
	})

	if result.stage != stageAskUser {
		t.Errorf("expected stageAskUser, got %d", result.stage)
	}
	if result.askRequestID != 100 {
		t.Errorf("expected requestID=100, got %d", result.askRequestID)
	}
	if result.askQuestion != "Pick one" {
		t.Errorf("expected question='Pick one', got '%s'", result.askQuestion)
	}
	if len(result.askOptions) != 3 {
		t.Errorf("expected 3 options, got %d", len(result.askOptions))
	}
	// composer should be blurred (options-only mode)
	if result.composer.Focused() {
		t.Error("expected composer blurred in options-only mode")
	}
}

func TestEnterAskUserFreeText(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming

	result := enterAskUser(m, backendAskUserRequestMsg{
		RequestID: 101,
		Question:  "What is your name?",
		Options:   nil,
		AllowText: true,
	})

	if result.stage != stageAskUser {
		t.Errorf("expected stageAskUser, got %d", result.stage)
	}
	// composer should be focused for free-text input
	if !result.composer.Focused() {
		t.Error("expected composer focused in free-text mode")
	}
	if result.composer.Placeholder != "Type your answer..." {
		t.Errorf("expected placeholder 'Type your answer...', got '%s'", result.composer.Placeholder)
	}
}

func TestEnterAskUserMixed(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming

	result := enterAskUser(m, backendAskUserRequestMsg{
		RequestID: 102,
		Question:  "Choose or type",
		Options:   []string{"X", "Y"},
		AllowText: true,
	})

	if result.stage != stageAskUser {
		t.Errorf("expected stageAskUser, got %d", result.stage)
	}
	// Mixed mode: allowText=true → composer should be focused
	if !result.composer.Focused() {
		t.Error("expected composer focused in mixed mode (allowText=true)")
	}
}

func TestAskUserArrowNavigation(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageAskUser
	m.askOptions = []string{"A", "B", "C"}
	m.askCursor = 0

	// Down
	updated, _ := handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyDown}))
	um := updated.(model)
	if um.askCursor != 1 {
		t.Errorf("expected cursor=1 after down, got %d", um.askCursor)
	}

	// Down again
	updated2, _ := handleAskUserKey(um, tea.KeyPressMsg(tea.Key{Code: tea.KeyDown}))
	um2 := updated2.(model)
	if um2.askCursor != 2 {
		t.Errorf("expected cursor=2 after second down, got %d", um2.askCursor)
	}

	// Up
	updated3, _ := handleAskUserKey(um2, tea.KeyPressMsg(tea.Key{Code: tea.KeyUp}))
	um3 := updated3.(model)
	if um3.askCursor != 1 {
		t.Errorf("expected cursor=1 after up, got %d", um3.askCursor)
	}
}

func TestAskUserArrowWrap(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageAskUser
	m.askOptions = []string{"A", "B", "C"}

	// Up from 0 → wraps to 2
	m.askCursor = 0
	updated, _ := handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyUp}))
	um := updated.(model)
	if um.askCursor != 2 {
		t.Errorf("expected cursor=2 (wrap from top), got %d", um.askCursor)
	}

	// Down from 2 → wraps to 0
	m.askCursor = 2
	updated2, _ := handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyDown}))
	um2 := updated2.(model)
	if um2.askCursor != 0 {
		t.Errorf("expected cursor=0 (wrap from bottom), got %d", um2.askCursor)
	}
}

func TestAskUserEnterSelectsOption(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageAskUser
	m.askRequestID = 200
	m.askOptions = []string{"Alpha", "Beta"}
	m.askCursor = 1 // Select "Beta"

	updated, _ := handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	if um.stage != stageStreaming {
		t.Errorf("expected stageStreaming after selection, got %d", um.stage)
	}
}

func TestAskUserEnterPrefersTypedText(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageAskUser
	m.askRequestID = 201
	m.askOptions = []string{"A", "B"}
	m.askAllowText = true
	m.askCursor = 0
	m.composer.Focus()
	m.composer.SetValue("custom answer")

	updated, cmd := handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	if um.stage != stageStreaming {
		t.Errorf("expected stageStreaming, got %d", um.stage)
	}
	// The command should include the custom answer (via Println)
	if cmd == nil {
		t.Error("expected non-nil command")
	}
}

func TestAskUserEscapeDefaultsFirst(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageAskUser
	m.askRequestID = 202
	m.askOptions = []string{"Default", "Other"}
	m.askCursor = 1

	updated, cmd := handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyEscape}))
	um := updated.(model)

	if um.stage != stageStreaming {
		t.Errorf("expected stageStreaming after escape, got %d", um.stage)
	}
	if cmd == nil {
		t.Error("expected non-nil command for Println")
	}
}

func TestAskUserEscapeEmptyOptions(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageAskUser
	m.askRequestID = 203
	m.askOptions = nil
	m.askAllowText = true

	updated, _ := handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyEscape}))
	um := updated.(model)

	if um.stage != stageStreaming {
		t.Errorf("expected stageStreaming after escape with no options, got %d", um.stage)
	}
}

func TestAskUserFocusRestored(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageAskUser
	m.askRequestID = 204
	m.askOptions = []string{"X"}
	m.askCursor = 0

	updated, _ := handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	if !um.composer.Focused() {
		t.Error("expected composer focused after ask-user answer")
	}
	if um.composer.Placeholder != "Ask AutoCode\u2026" {
		t.Errorf("expected placeholder restored to 'Ask AutoCode\u2026', got '%s'", um.composer.Placeholder)
	}
}

func TestRenderAskUserWithOptions(t *testing.T) {
	m := initialModel(nil)
	m.askQuestion = "Which option?"
	m.askOptions = []string{"First", "Second", "Third"}
	m.askCursor = 1
	m.askAllowText = false

	view := renderAskUserView(m)

	if !strings.Contains(view, "Which option?") {
		t.Error("expected question in view")
	}
	if !strings.Contains(view, "First") {
		t.Error("expected option 'First' in view")
	}
	if !strings.Contains(view, "Second") {
		t.Error("expected option 'Second' in view")
	}
	if !strings.Contains(view, "Third") {
		t.Error("expected option 'Third' in view")
	}
}

func TestRenderAskUserFreeText(t *testing.T) {
	m := initialModel(nil)
	m.askQuestion = "What is your name?"
	m.askOptions = nil
	m.askAllowText = true
	m.composer.Focus()

	view := renderAskUserView(m)

	if !strings.Contains(view, "What is your name?") {
		t.Error("expected question in view")
	}
	if !strings.Contains(view, "type your answer") {
		t.Error("expected free-text prompt in view")
	}
}

func TestAskUserMultiStageFlow(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming

	// First ask-user
	updated, _ := m.Update(backendAskUserRequestMsg{
		RequestID: 300,
		Question:  "First Q",
		Options:   []string{"A"},
	})
	um := updated.(model)
	if um.stage != stageAskUser {
		t.Fatalf("expected stageAskUser, got %d", um.stage)
	}

	// Answer first ask-user
	updated2, _ := handleAskUserKey(um, tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um2 := updated2.(model)
	if um2.stage != stageStreaming {
		t.Fatalf("expected stageStreaming after answer, got %d", um2.stage)
	}

	// Second ask-user arrives
	updated3, _ := um2.Update(backendAskUserRequestMsg{
		RequestID: 301,
		Question:  "Second Q",
		Options:   []string{"X", "Y"},
	})
	um3 := updated3.(model)
	if um3.stage != stageAskUser {
		t.Fatalf("expected stageAskUser for second question, got %d", um3.stage)
	}
	if um3.askQuestion != "Second Q" {
		t.Errorf("expected question='Second Q', got '%s'", um3.askQuestion)
	}

	// Answer second ask-user
	updated4, _ := handleAskUserKey(um3, tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um4 := updated4.(model)
	if um4.stage != stageStreaming {
		t.Errorf("expected stageStreaming after second answer, got %d", um4.stage)
	}
}

func TestAskUserSelectionHighlights(t *testing.T) {
	m := initialModel(nil)
	m.askQuestion = "Pick"
	m.askOptions = []string{"A", "B"}
	m.askCursor = 0

	view := renderAskUserView(m)

	// Selected option should have the cursor indicator
	if !strings.Contains(view, "❯") {
		t.Error("expected cursor indicator ❯ in view")
	}
}

func TestAskUserTypingDuringOptions(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageAskUser
	m.askOptions = []string{"A", "B"}
	m.askAllowText = true
	m.askCursor = 0
	m.composer.Focus()

	// Type a character
	updated, _ := handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Text: "z", Code: 'z'}))
	um := updated.(model)

	if um.composer.Value() != "z" {
		t.Errorf("expected composer value='z' during options with allowText, got '%s'", um.composer.Value())
	}
}

func TestAskUserEscWithCtrlC(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageAskUser
	m.askRequestID = 205
	m.askOptions = []string{"A"}
	m.askCursor = 0

	updated, _ := handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: 'c', Mod: tea.ModCtrl}))
	um := updated.(model)

	if um.stage != stageStreaming {
		t.Errorf("expected stageStreaming after Ctrl+C in ask-user, got %d", um.stage)
	}
}

func TestAskUserVimNavigation(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageAskUser
	m.askOptions = []string{"A", "B", "C"}
	m.askCursor = 0

	// 'j' moves down (vim binding)
	updated, _ := handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Text: "j", Code: 'j'}))
	um := updated.(model)
	if um.askCursor != 1 {
		t.Errorf("expected cursor=1 after 'j', got %d", um.askCursor)
	}

	// 'k' moves up (vim binding)
	updated2, _ := handleAskUserKey(um, tea.KeyPressMsg(tea.Key{Text: "k", Code: 'k'}))
	um2 := updated2.(model)
	if um2.askCursor != 0 {
		t.Errorf("expected cursor=0 after 'k', got %d", um2.askCursor)
	}
}

func TestAskUserEnterEmptyFreeTextNoOptions(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageAskUser
	m.askRequestID = 206
	m.askOptions = nil
	m.askAllowText = true
	m.composer.Focus()
	m.composer.SetValue("") // empty text

	updated, _ := handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	// Should stay in ask-user (no answer provided)
	if um.stage != stageAskUser {
		t.Errorf("expected to stay in stageAskUser with empty text and no options, got %d", um.stage)
	}
}
