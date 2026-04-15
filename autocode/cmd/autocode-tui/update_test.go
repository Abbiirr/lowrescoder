package main

import (
	"strings"
	"testing"

	tea "charm.land/bubbletea/v2"
)

func TestUpdateWindowSizeMsg(t *testing.T) {
	m := initialModel(nil)
	updated, cmd := m.Update(tea.WindowSizeMsg{Width: 120, Height: 40})
	um := updated.(model)
	if um.width != 120 {
		t.Errorf("expected width=120, got %d", um.width)
	}
	if um.height != 40 {
		t.Errorf("expected height=40, got %d", um.height)
	}
	// Codex Entry 1071 blocker #2: resize must force an immediate render
	// cycle so streaming/spinner/tool rows pick up the new width without
	// waiting for the next backend token. The handler now returns tickCmd()
	// instead of nil — verify the returned cmd is non-nil.
	if cmd == nil {
		t.Error("expected WindowSizeMsg to return a non-nil cmd (tickCmd) for immediate re-render")
	}
	// The composer width should also have been recomputed
	if um.statusBar.Width != 120 {
		t.Errorf("expected statusBar.Width=120, got %d", um.statusBar.Width)
	}
}

func TestUpdateWindowSizeMsgNarrow(t *testing.T) {
	// At a narrow width, the composer should still accept the WindowSizeMsg
	// without panicking. Regression guard for Codex Entry 1071 blocker #2.
	m := initialModel(nil)
	updated, cmd := m.Update(tea.WindowSizeMsg{Width: 40, Height: 24})
	um := updated.(model)
	if um.width != 40 {
		t.Errorf("expected width=40, got %d", um.width)
	}
	if cmd == nil {
		t.Error("expected non-nil cmd even at narrow width")
	}
}

func TestUpdateStatusMsg(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInit

	updated, _ := m.Update(backendStatusMsg{
		Model:    "qwen3:8b",
		Provider: "openrouter",
		Mode:     "suggest",
	})
	um := updated.(model)

	if um.stage != stageInput {
		t.Errorf("expected stageInput after status, got %d", um.stage)
	}
	if um.statusBar.Model != "qwen3:8b" {
		t.Errorf("expected model=qwen3:8b, got %s", um.statusBar.Model)
	}
	if um.statusBar.Provider != "openrouter" {
		t.Errorf("expected provider=openrouter, got %s", um.statusBar.Provider)
	}
}

func TestUpdateStatusMsgDoesNotChangeStageIfNotInit(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming

	updated, _ := m.Update(backendStatusMsg{
		Model: "qwen3:8b",
		Mode:  "suggest",
	})
	um := updated.(model)

	if um.stage != stageStreaming {
		t.Errorf("expected stageStreaming unchanged, got %d", um.stage)
	}
}

func TestUpdateTokenMsg(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming

	updated, cmd := m.Update(backendTokenMsg{Text: "hello "})
	um := updated.(model)

	if um.tokenBuf.String() != "hello " {
		t.Errorf("expected tokenBuf='hello ', got '%s'", um.tokenBuf.String())
	}
	if !um.streamDirty {
		t.Error("expected streamDirty=true")
	}
	if cmd == nil {
		t.Error("expected tickCmd to be returned")
	}
}

func TestUpdateTokenMsgNoDuplicateTick(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.streamDirty = true

	updated, cmd := m.Update(backendTokenMsg{Text: "world "})
	um := updated.(model)

	if um.tokenBuf.String() != "world " {
		t.Errorf("expected tokenBuf='world ', got '%s'", um.tokenBuf.String())
	}
	// Should NOT return a new tick since streamDirty was already true
	if cmd != nil {
		t.Error("expected no tick command when already dirty")
	}
}

func TestUpdateThinkingMsg(t *testing.T) {
	m := initialModel(nil)
	updated, cmd := m.Update(backendThinkingMsg{Text: "reasoning..."})
	um := updated.(model)
	if um.thinkingBuf.String() != "reasoning..." {
		t.Errorf("expected thinkingBuf='reasoning...', got '%s'", um.thinkingBuf.String())
	}
	// Should return a tickCmd to force view refresh for live display
	if cmd == nil {
		t.Error("expected tickCmd for thinking token view refresh")
	}
}

func TestUpdateToolCallMsg(t *testing.T) {
	m := initialModel(nil)
	updated, _ := m.Update(backendToolCallMsg{
		Name:   "read_file",
		Status: "running",
	})
	um := updated.(model)

	if len(um.toolCalls) != 1 {
		t.Fatalf("expected 1 tool call, got %d", len(um.toolCalls))
	}
	if um.toolCalls[0].Name != "read_file" {
		t.Errorf("expected name=read_file, got %s", um.toolCalls[0].Name)
	}
}

func TestUpdateToolCallMsgUpdatesExisting(t *testing.T) {
	m := initialModel(nil)
	m.toolCalls = []toolCallEntry{{Name: "read_file", Status: "running"}}

	updated, _ := m.Update(backendToolCallMsg{
		Name:   "read_file",
		Status: "completed",
		Result: "file contents",
	})
	um := updated.(model)

	if len(um.toolCalls) != 1 {
		t.Fatalf("expected 1 tool call, got %d", len(um.toolCalls))
	}
	if um.toolCalls[0].Status != "completed" {
		t.Errorf("expected status=completed, got %s", um.toolCalls[0].Status)
	}
}

func TestUpdateErrorMsg(t *testing.T) {
	m := initialModel(nil)
	updated, _ := m.Update(backendErrorMsg{Message: "something broke"})
	um := updated.(model)
	if um.lastError != "something broke" {
		t.Errorf("expected lastError='something broke', got '%s'", um.lastError)
	}
}

func TestUpdateExitMsg(t *testing.T) {
	m := initialModel(nil)
	updated, cmd := m.Update(backendExitMsg{Err: nil})
	um := updated.(model)
	if !um.quitting {
		t.Error("expected quitting=true")
	}
	if cmd == nil {
		t.Error("expected Quit command")
	}
}

func TestUpdateTickMsg(t *testing.T) {
	m := initialModel(nil)
	m.tokenBuf.WriteString("some tokens ")
	m.streamDirty = true

	updated, _ := m.Update(tickMsg{})
	um := updated.(model)

	if um.streamBuf.String() != "some tokens " {
		t.Errorf("expected streamBuf='some tokens ', got '%s'", um.streamBuf.String())
	}
	if um.tokenBuf.Len() != 0 {
		t.Error("expected tokenBuf to be reset after tick")
	}
	if um.streamDirty {
		t.Error("expected streamDirty=false after tick")
	}
}

func TestUpdateTickMsgNotDirty(t *testing.T) {
	m := initialModel(nil)
	m.streamDirty = false

	updated, _ := m.Update(tickMsg{})
	um := updated.(model)

	if um.streamBuf.Len() != 0 {
		t.Error("expected streamBuf empty when not dirty")
	}
}

func TestHandleInputKeyCtrlCFirstPress(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: 'c', Mod: tea.ModCtrl}))
	um := updated.(model)

	if um.interruptCount != 1 {
		t.Errorf("expected interruptCount=1, got %d", um.interruptCount)
	}
	if um.quitting {
		t.Error("should not quit on first Ctrl+C")
	}
}

func TestHandleInputKeyCtrlCSecondPress(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.interruptCount = 1

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: 'c', Mod: tea.ModCtrl}))
	um := updated.(model)

	if !um.quitting {
		t.Error("should quit on second Ctrl+C")
	}
}

func TestHandleInputKeyCtrlD(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, cmd := m.Update(tea.KeyPressMsg(tea.Key{Code: 'd', Mod: tea.ModCtrl}))
	um := updated.(model)

	if !um.quitting {
		t.Error("expected quitting=true on Ctrl+D")
	}
	if cmd == nil {
		t.Error("expected Quit command")
	}
}

func TestHandleInputKeyEnterEmpty(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.composer.SetValue("")

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	if um.stage != stageInput {
		t.Error("should stay in input stage when text is empty")
	}
}

func TestHandleStreamingKeyCtrlCEntersSteer(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.messageQueue = []string{"queued msg"}

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: 'c', Mod: tea.ModCtrl}))
	um := updated.(model)

	if um.stage != stageSteer {
		t.Errorf("expected stageSteer after Ctrl+C, got %d", um.stage)
	}
	if !um.stageSteer {
		t.Error("expected stageSteer flag to be true")
	}
}

func TestHandleStreamingKeyEscape(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.messageQueue = []string{"queued msg"}

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEscape}))
	um := updated.(model)

	if um.messageQueue != nil {
		t.Error("expected queue to be cleared on escape")
	}
}

func TestHandleStreamingKeyEnterQueues(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.composer.SetValue("next message")

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	if len(um.messageQueue) != 1 {
		t.Fatalf("expected 1 queued message, got %d", len(um.messageQueue))
	}
	if um.messageQueue[0] != "next message" {
		t.Errorf("expected 'next message', got '%s'", um.messageQueue[0])
	}
}

func TestHandleStreamingKeyEnterQueueFull(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.queueMax = 2
	m.messageQueue = []string{"a", "b"}
	m.composer.SetValue("overflow")

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	if len(um.messageQueue) != 2 {
		t.Errorf("expected queue to stay at 2, got %d", len(um.messageQueue))
	}
}

func TestHandleDoneResetsState(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.tokenBuf.WriteString("remaining ")
	m.streamBuf.WriteString("content ")
	m.thinkingBuf.WriteString("thought")
	m.toolCalls = []toolCallEntry{{Name: "test", Status: "completed"}}

	updated, _ := m.Update(backendDoneMsg{TokensIn: 100, TokensOut: 200})
	um := updated.(model)

	if um.stage != stageInput {
		t.Errorf("expected stageInput after done, got %d", um.stage)
	}
	if um.streamBuf.Len() != 0 {
		t.Error("expected streamBuf reset")
	}
	if um.thinkingBuf.Len() != 0 {
		t.Error("expected thinkingBuf reset")
	}
	if len(um.toolCalls) != 0 {
		t.Error("expected toolCalls reset")
	}
}

func TestHandleDoneUpdatesStats(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.statusBar.Tokens = 50

	updated, _ := m.Update(backendDoneMsg{TokensIn: 100, TokensOut: 200})
	um := updated.(model)

	if um.statusBar.Tokens != 350 {
		t.Errorf("expected tokens=350, got %d", um.statusBar.Tokens)
	}
}

func TestHandleDoneDrainsQueue(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.messageQueue = []string{"next"}

	_, cmd := m.Update(backendDoneMsg{})

	// Should return a batch that includes queue drain
	if cmd == nil {
		t.Error("expected a command (including queue drain)")
	}
}

func TestHandleSlashCommandExit(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.composer.SetValue("/exit")

	updated, _ := m.handleSlashCommand("/exit")
	um := updated.(model)

	if !um.quitting {
		t.Error("expected quitting=true for /exit")
	}
}

func TestHandleSlashCommandThinking(t *testing.T) {
	m := initialModel(nil)
	m.showThinking = false

	updated, _ := m.handleSlashCommand("/thinking")
	um := updated.(model)

	if !um.showThinking {
		t.Error("expected showThinking=true after /thinking toggle")
	}

	updated2, _ := um.handleSlashCommand("/thinking")
	um2 := updated2.(model)

	if um2.showThinking {
		t.Error("expected showThinking=false after second /thinking toggle")
	}
}

func TestApprovalRequestTransition(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming

	updated, _ := m.Update(backendApprovalRequestMsg{
		RequestID: 1000,
		Tool:      "write_file",
		Args:      `{"path": "/tmp/test"}`,
	})
	um := updated.(model)

	if um.stage != stageApproval {
		t.Errorf("expected stageApproval, got %d", um.stage)
	}
	if um.approvalRequestID != 1000 {
		t.Errorf("expected requestID=1000, got %d", um.approvalRequestID)
	}
	if um.approvalTool != "write_file" {
		t.Errorf("expected tool=write_file, got %s", um.approvalTool)
	}
}

// --- Parallel typing tests ---

func TestTextInputStaysFocusedDuringStreaming(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.composer.SetValue("hello world")

	// sendChat should NOT blur the composer
	um, _ := m.sendChat("hello world")
	result := um.(model)

	if result.stage != stageStreaming {
		t.Errorf("expected stageStreaming, got %d", result.stage)
	}
	// composer should still be focused (not blurred)
	if !result.composer.Focused() {
		t.Error("expected composer to remain focused during streaming for parallel typing")
	}
}

func TestTypingDuringStreaming(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	// composer should be focused for parallel typing
	m.composer.Focus()

	// Simulate typing a character during streaming
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Text: "a", Code: 'a'}))
	um := updated.(model)

	if um.composer.Value() != "a" {
		t.Errorf("expected composer value='a' during streaming, got '%s'", um.composer.Value())
	}
	// Should still be streaming
	if um.stage != stageStreaming {
		t.Errorf("expected to stay in stageStreaming, got %d", um.stage)
	}
}

func TestQueueMessageDuringStreamingPreservesInput(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.composer.Focus()
	m.composer.SetValue("queued message")

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	// Message should be queued
	if len(um.messageQueue) != 1 || um.messageQueue[0] != "queued message" {
		t.Errorf("expected 'queued message' in queue, got %v", um.messageQueue)
	}
	// composer should be cleared after queuing
	if um.composer.Value() != "" {
		t.Errorf("expected composer cleared after queue, got '%s'", um.composer.Value())
	}
	// Should still be focused for more parallel typing
	if !um.composer.Focused() {
		t.Error("expected composer to remain focused after queuing")
	}
}

func TestCtrlCEntersSteerDuringStreaming(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.composer.Focus()
	m.messageQueue = []string{"a", "b"}
	m.interruptCount = 0

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: 'c', Mod: tea.ModCtrl}))
	um := updated.(model)

	// First Ctrl+C enters steer mode
	if um.stage != stageSteer {
		t.Errorf("expected stageSteer after Ctrl+C, got %d", um.stage)
	}
	if !um.stageSteer {
		t.Error("expected stageSteer flag to be true")
	}
	// Queue is preserved (not cleared) — steer can be sent or cancelled
	if um.messageQueue == nil {
		t.Error("expected queue preserved during steer, got nil")
	}
	// interruptCount should be 1 (second Ctrl+C will force quit)
	if um.interruptCount != 1 {
		t.Errorf("expected interruptCount=1, got %d", um.interruptCount)
	}
}

func TestDoubleCtrlCDuringStreamingQuits(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.interruptCount = 0

	// First Ctrl+C: enter steer mode, don't quit
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: 'c', Mod: tea.ModCtrl}))
	um := updated.(model)
	if um.quitting {
		t.Error("first Ctrl+C should enter steer mode, not quit")
	}
	if um.stage != stageSteer {
		t.Errorf("expected stageSteer after first Ctrl+C, got %d", um.stage)
	}
	if um.interruptCount != 1 {
		t.Errorf("expected interruptCount=1 after first Ctrl+C, got %d", um.interruptCount)
	}

	// Second Ctrl+C: force quit
	updated2, _ := um.Update(tea.KeyPressMsg(tea.Key{Code: 'c', Mod: tea.ModCtrl}))
	um2 := updated2.(model)
	if !um2.quitting {
		t.Error("second Ctrl+C should force-quit during streaming")
	}
}

func TestCtrlCDuringInputFirstPress(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.interruptCount = 0

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: 'c', Mod: tea.ModCtrl}))
	um := updated.(model)

	if um.interruptCount != 1 {
		t.Errorf("expected interruptCount=1, got %d", um.interruptCount)
	}
	if um.quitting {
		t.Error("should NOT quit on first Ctrl+C in input mode")
	}
}

func TestCtrlCDuringInputSecondPress(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.interruptCount = 1

	updated, cmd := m.Update(tea.KeyPressMsg(tea.Key{Code: 'c', Mod: tea.ModCtrl}))
	um := updated.(model)

	if !um.quitting {
		t.Error("should quit on second Ctrl+C in input mode")
	}
	if cmd == nil {
		t.Error("expected Quit command on second Ctrl+C")
	}
}

func TestEscapeDuringStreamingCancels(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.messageQueue = []string{"pending"}

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEscape}))
	um := updated.(model)

	if um.messageQueue != nil {
		t.Errorf("expected queue cleared on Escape, got %v", um.messageQueue)
	}
}

func TestInputFocusRestoredAfterApproval(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageApproval
	m.approvalRequestID = 1000
	m.approvalCursor = 0 // "Yes"

	updated, _ := handleApprovalKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	if um.stage != stageStreaming {
		t.Errorf("expected stageStreaming after approval, got %d", um.stage)
	}
	if !um.composer.Focused() {
		t.Error("expected composer focused after approval for parallel typing")
	}
}

func TestInputFocusRestoredAfterApprovalDenied(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageApproval
	m.approvalRequestID = 1000

	updated, _ := handleApprovalKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyEscape}))
	um := updated.(model)

	if um.stage != stageStreaming {
		t.Errorf("expected stageStreaming after denial, got %d", um.stage)
	}
	if !um.composer.Focused() {
		t.Error("expected composer focused after denial for parallel typing")
	}
}

func TestInputFocusRestoredAfterAskUser(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageAskUser
	m.askRequestID = 1001
	m.askOptions = []string{"A", "B"}
	m.askCursor = 0

	updated, _ := handleAskUserKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	if um.stage != stageStreaming {
		t.Errorf("expected stageStreaming after ask-user, got %d", um.stage)
	}
	if !um.composer.Focused() {
		t.Error("expected composer focused after ask-user for parallel typing")
	}
}

func TestAskUserRequestTransition(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming

	updated, _ := m.Update(backendAskUserRequestMsg{
		RequestID: 1001,
		Question:  "Choose?",
		Options:   []string{"A", "B"},
		AllowText: true,
	})
	um := updated.(model)

	if um.stage != stageAskUser {
		t.Errorf("expected stageAskUser, got %d", um.stage)
	}
	if um.askQuestion != "Choose?" {
		t.Errorf("expected question='Choose?', got '%s'", um.askQuestion)
	}
}

// --- Display pipeline tests ---

func TestTokensAppearInStreamBuf(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming

	// Send token
	updated, _ := m.Update(backendTokenMsg{Text: "hello "})
	m = updated.(model)

	// Token is in tokenBuf, not streamBuf yet
	if m.tokenBuf.String() != "hello " {
		t.Errorf("expected tokenBuf='hello ', got '%s'", m.tokenBuf.String())
	}
	if m.streamBuf.Len() != 0 {
		t.Error("expected streamBuf empty before tick")
	}

	// Tick flushes to streamBuf
	updated, _ = m.Update(tickMsg{})
	m = updated.(model)

	if m.streamBuf.String() != "hello " {
		t.Errorf("expected streamBuf='hello ' after tick, got '%s'", m.streamBuf.String())
	}
	if m.tokenBuf.Len() != 0 {
		t.Error("expected tokenBuf empty after tick")
	}
}

func TestDoneCommitsContentViaTeaPrintln(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.width = 80
	m.streamBuf.WriteString("Some response content")

	_, cmd := m.Update(backendDoneMsg{TokensIn: 10, TokensOut: 20})

	// handleDone should return a non-nil command batch
	if cmd == nil {
		t.Fatal("expected non-nil command from handleDone (tea.Println batch)")
	}
}

func TestDoneWithEmptyStreamBuf(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.width = 80
	// streamBuf is empty

	updated, cmd := m.Update(backendDoneMsg{TokensIn: 0, TokensOut: 0})
	um := updated.(model)

	// Should still return a command (at least separator Println)
	if cmd == nil {
		t.Error("expected non-nil command even with empty streamBuf (separator)")
	}
	if um.stage != stageInput {
		t.Errorf("expected stageInput after done, got %d", um.stage)
	}
}

func TestMultipleTokensAccumulate(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming

	// First token starts dirty + tick
	updated, _ := m.Update(backendTokenMsg{Text: "hello "})
	m = updated.(model)

	// Second token accumulates (no new tick)
	updated, _ = m.Update(backendTokenMsg{Text: "world "})
	m = updated.(model)

	// Third token
	updated, _ = m.Update(backendTokenMsg{Text: "!"})
	m = updated.(model)

	if m.tokenBuf.String() != "hello world !" {
		t.Errorf("expected tokenBuf='hello world !', got '%s'", m.tokenBuf.String())
	}
}

func TestTickFlushesAllTokens(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming

	// Accumulate multiple tokens
	m.tokenBuf.WriteString("first ")
	m.tokenBuf.WriteString("second ")
	m.tokenBuf.WriteString("third")
	m.streamDirty = true

	updated, _ := m.Update(tickMsg{})
	m = updated.(model)

	if m.streamBuf.String() != "first second third" {
		t.Errorf("expected all tokens flushed, got '%s'", m.streamBuf.String())
	}
}

func TestTokensDuringStageInputDontCrash(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	// Tokens arriving during input stage should not crash and print directly
	_, cmd := m.Update(backendTokenMsg{Text: "unexpected token"})

	// Should return a Println command (direct print, not buffered)
	if cmd == nil {
		t.Error("expected Println command for tokens during input stage")
	}
}

func TestDoneFlushesRemainingTokenBuf(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.width = 80
	m.tokenBuf.WriteString("unflushed tokens")
	m.streamBuf.WriteString("already flushed ")

	updated, _ := m.Update(backendDoneMsg{TokensIn: 10, TokensOut: 20})
	um := updated.(model)

	// After done, both buffers should be reset (content was rendered)
	if um.streamBuf.Len() != 0 {
		t.Error("expected streamBuf reset after done")
	}
	if um.tokenBuf.Len() != 0 {
		t.Error("expected tokenBuf reset after done")
	}
}

// --- Thinking token tests ---

func TestThinkingTokensAccumulate(t *testing.T) {
	m := initialModel(nil)

	updated, _ := m.Update(backendThinkingMsg{Text: "first thought "})
	m = updated.(model)
	updated, _ = m.Update(backendThinkingMsg{Text: "second thought"})
	m = updated.(model)

	if m.thinkingBuf.String() != "first thought second thought" {
		t.Errorf("expected accumulated thinking, got '%s'", m.thinkingBuf.String())
	}
}

func TestThinkingResetOnDone(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.thinkingBuf.WriteString("some thinking")

	updated, _ := m.Update(backendDoneMsg{})
	um := updated.(model)

	if um.thinkingBuf.Len() != 0 {
		t.Error("expected thinkingBuf reset after done")
	}
}

// --- Ctrl+D tests ---

func TestCtrlDQuitsFromStreaming(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming

	// Ctrl+D should force-quit even during streaming
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: 'd', Mod: tea.ModCtrl}))
	um := updated.(model)

	if !um.quitting {
		t.Error("Ctrl+D should force-quit during streaming")
	}
}

// --- Queue count tests ---

func TestQueueCountInView(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.streamBuf.WriteString("streaming")
	m.messageQueue = []string{"a", "b", "c"}

	// View sets statusBar.Queue and renders it
	view := m.View().Content

	if !strings.Contains(view, "queue: 3") {
		t.Errorf("expected 'queue: 3' in view, got:\n%s", view)
	}
}

// --- Interrupt count reset on send ---

func TestInterruptCountResetsOnSend(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.interruptCount = 1
	m.composer.SetValue("hello")

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	if um.interruptCount != 0 {
		t.Errorf("expected interruptCount=0 after send, got %d", um.interruptCount)
	}
}

// --- sendChat produces echo command ---

func TestSendChatProducesEchoCommand(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	_, cmd := m.sendChat("test message")
	if cmd == nil {
		t.Error("expected echo Println command from sendChat")
	}
}

// --- Slash command end-to-end tests ---

func TestSlashExitViaEnter(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.composer.SetValue("/exit")

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	if !um.quitting {
		t.Error("expected quitting=true after /exit Enter")
	}
}

func TestSlashThinkingViaEnter(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.showThinking = true
	m.composer.SetValue("/thinking")

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	if um.showThinking {
		t.Error("expected showThinking=false after /thinking toggle")
	}
}

func TestSlashCommandBackendDelegatedNoBackend(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.composer.SetValue("/help")

	updated, cmd := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	// Should not crash with nil backend
	if um.quitting {
		t.Error("should not quit on /help")
	}
	// Should return a command (error message Println) since no backend
	if cmd == nil {
		t.Error("expected error Println command when backend is nil")
	}
}

func TestEnterAcceptsAutocompleteSuggestion(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	// Type "/hel" to get a single suggestion (/help)
	for _, r := range []rune{'/', 'h', 'e', 'l'} {
		updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Text: string(r), Code: r}))
		m = updated.(model)
	}

	// Should have /help as a completion
	if len(m.completions) == 0 {
		t.Fatal("expected completions after typing /hel")
	}

	// Press Enter — single completion auto-accepts, submits /help
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	m = updated.(model)

	// Composer should be cleared after submission
	if m.composer.Value() != "" {
		t.Errorf("expected composer cleared after Enter, got '%s'", m.composer.Value())
	}
}

func TestTokensDuringInputPrintDirectly(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	// Token arriving during input stage should print directly
	_, cmd := m.Update(backendTokenMsg{Text: "[System] Available commands: /help, /exit"})

	// Should return a Println command (not nil)
	if cmd == nil {
		t.Error("expected Println command for tokens during input stage")
	}
	// tokenBuf should remain empty (not buffered)
	if m.tokenBuf.Len() != 0 {
		t.Error("expected tokenBuf empty when printing directly in input stage")
	}
}

func TestSlashCommandClearsCompletions(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.completions = []string{"/exit", "/explore"}
	m.composer.SetValue("/exit")

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	if um.completions != nil {
		t.Errorf("expected completions cleared after slash command, got %v", um.completions)
	}
}

// --- updateCompletions tests ---

func TestUpdateCompletionsForSlashInput(t *testing.T) {
	m := initialModel(nil)
	m.composer.SetValue("/he")
	m.updateCompletions()

	if len(m.completions) == 0 {
		t.Fatal("expected completions for /he")
	}
}

func TestUpdateCompletionsClearsForNonSlash(t *testing.T) {
	m := initialModel(nil)
	m.composer.SetValue("hello")
	m.updateCompletions()

	if m.completions != nil {
		t.Errorf("expected nil completions for non-slash, got %v", m.completions)
	}
}

func TestUpdateCompletionsClearsAfterSpace(t *testing.T) {
	m := initialModel(nil)
	m.composer.SetValue("/help arg")
	m.updateCompletions()

	if m.completions != nil {
		t.Errorf("expected nil completions after space in command, got %v", m.completions)
	}
}

// --- /resume command tests ---

func TestSlashResumeNoArgsTriggersSessionList(t *testing.T) {
	b := NewBackend()
	m := initialModel(b)
	m.stage = stageInput

	_, cmd := m.handleSlashCommand("/resume")

	// Should return a non-nil command (the SendRequestCmd that will call session.list)
	if cmd == nil {
		t.Error("expected non-nil command from /resume without args")
	}

	// The SendRequestCmd sends a session.list RPC to the backend
	select {
	case data := <-b.writeCh:
		s := string(data)
		if !strings.Contains(s, "session.list") {
			t.Errorf("expected session.list in RPC, got %s", s)
		}
	default:
		t.Error("expected session.list message in writeCh")
	}
}

func TestSlashResumeWithArgsDelegatesToBackend(t *testing.T) {
	b := NewBackend()
	m := initialModel(b)
	m.stage = stageInput

	_, cmd := m.handleSlashCommand("/resume abc123")

	// Should return a Println command for confirmation
	if cmd == nil {
		t.Error("expected Println command for direct resume")
	}

	// Should send session.resume directly with the given ID
	select {
	case data := <-b.writeCh:
		s := string(data)
		if !strings.Contains(s, "session.resume") {
			t.Errorf("expected session.resume in RPC, got %s", s)
		}
		if !strings.Contains(s, "abc123") {
			t.Errorf("expected session_id=abc123 in RPC, got %s", s)
		}
	default:
		t.Error("expected session.resume message in writeCh")
	}
}

func TestSlashResumeNoBackend(t *testing.T) {
	m := initialModel(nil) // nil backend
	m.stage = stageInput

	_, cmd := m.handleSlashCommand("/resume")

	// Should return error message Println
	if cmd == nil {
		t.Error("expected error Println command when backend is nil")
	}
}

func TestBackendSessionListMsgEntersSessionPicker(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	sessions := []sessionEntry{
		{ID: "id1", Title: "Session 1", Model: "m1"},
		{ID: "id2", Title: "Session 2", Model: "m2"},
	}

	updated, _ := m.Update(backendSessionListMsg{Sessions: sessions})
	um := updated.(model)

	if um.stage != stageAskUser {
		t.Errorf("expected stageAskUser, got %d", um.stage)
	}
	if um.askRequestID != -1 {
		t.Errorf("expected sentinel askRequestID=-1, got %d", um.askRequestID)
	}
	if len(um.askOptions) != 2 {
		t.Errorf("expected 2 options, got %d", len(um.askOptions))
	}
}

func TestBackendSessionListMsgEmptySessions(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, _ := m.Update(backendSessionListMsg{Sessions: []sessionEntry{}})
	um := updated.(model)

	// Should NOT enter session picker, should show error
	if um.stage == stageAskUser {
		t.Error("should not enter session picker with empty sessions")
	}
	if um.lastError != "No sessions found" {
		t.Errorf("expected error message 'No sessions found', got '%s'", um.lastError)
	}
}

func TestSlashResumeWithArgsTrimsWhitespace(t *testing.T) {
	b := NewBackend()
	m := initialModel(b)
	m.stage = stageInput

	m.handleSlashCommand("/resume   abc123   ")

	select {
	case data := <-b.writeCh:
		s := string(data)
		if !strings.Contains(s, "abc123") {
			t.Errorf("expected trimmed session ID 'abc123', got %s", s)
		}
	default:
		t.Error("expected message in writeCh")
	}
}

func TestSlashResumeViaEnter(t *testing.T) {
	// Test the full path: type /resume, press Enter
	m := initialModel(nil)
	m.stage = stageInput
	m.composer.SetValue("/resume")

	updated, cmd := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	// With nil backend, should get error message
	if um.quitting {
		t.Error("should not quit on /resume")
	}
	if cmd == nil {
		t.Error("expected error command when backend nil")
	}
}

// --- Token empty text test ---

func TestTokenMsgEmptyText(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming

	// Empty text token during streaming should not crash
	updated, _ := m.Update(backendTokenMsg{Text: ""})
	um := updated.(model)

	if um.tokenBuf.String() != "" {
		t.Errorf("expected empty tokenBuf for empty text, got '%s'", um.tokenBuf.String())
	}
}

func TestTokenMsgEmptyTextDuringInput(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	// Empty text during input stage
	_, cmd := m.Update(backendTokenMsg{Text: ""})

	// Empty text should not produce a Println (trimmed to empty)
	if cmd != nil {
		t.Error("expected nil command for empty token during input stage")
	}
}

// --- Phase 3: Sliding window tests ---

func TestTickFlushesStableLinesToScrollback(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.maxLiveLines = 3
	// Write 6 lines of content to tokenBuf
	for i := 0; i < 6; i++ {
		m.tokenBuf.WriteString("line " + strings.Repeat("x", i+1))
		m.tokenBuf.WriteString("\n")
	}
	m.streamDirty = true

	updated, cmd := m.Update(tickMsg{})
	um := updated.(model)

	// First 3 lines should be flushed to stableScrollbackLines
	if len(um.stableScrollbackLines) < 3 {
		t.Errorf("expected at least 3 stable lines, got %d", len(um.stableScrollbackLines))
	}
	// streamBuf should only contain the last maxLiveLines
	lines := strings.Split(um.streamBuf.String(), "\n")
	// Filter empty trailing line from trailing newline
	nonEmpty := 0
	for _, l := range lines {
		if l != "" {
			nonEmpty++
		}
	}
	if nonEmpty > m.maxLiveLines {
		t.Errorf("expected at most %d live lines, got %d", m.maxLiveLines, nonEmpty)
	}
	// Should have produced tea.Println commands for flushed lines
	if cmd == nil {
		t.Error("expected tea.Println commands for flushed stable lines")
	}
}

func TestTickNoFlushWhenBelowMaxLiveLines(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.maxLiveLines = 10
	m.tokenBuf.WriteString("short content\n")
	m.streamDirty = true

	updated, _ := m.Update(tickMsg{})
	um := updated.(model)

	if len(um.stableScrollbackLines) != 0 {
		t.Errorf("expected no stable lines for short content, got %d", len(um.stableScrollbackLines))
	}
}

// --- Phase 4: Steer mode tests ---

func TestSteerModeEnterOnCtrlC(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: 'c', Mod: tea.ModCtrl}))
	um := updated.(model)

	if um.stage != stageSteer {
		t.Errorf("expected stageSteer, got %d", um.stage)
	}
	if !um.stageSteer {
		t.Error("expected stageSteer flag")
	}
}

func TestSteerModeEscapeReturnsToStreaming(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageSteer
	m.stageSteer = true
	m.steerInput = "partial"

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEscape}))
	um := updated.(model)

	if um.stage != stageStreaming {
		t.Errorf("expected stageStreaming, got %d", um.stage)
	}
	if um.stageSteer {
		t.Error("expected stageSteer to be cleared")
	}
}

func TestSteerModeCtrlCQuitsOnSecondPress(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageSteer
	m.stageSteer = true
	m.interruptCount = 1

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: 'c', Mod: tea.ModCtrl}))
	um := updated.(model)

	if !um.quitting {
		t.Error("expected second Ctrl+C to force-quit")
	}
}

func TestSteerModeEnterSendsMessage(t *testing.T) {
	b := NewBackend()
	m := initialModel(b)
	m.stage = stageSteer
	m.stageSteer = true
	m.steerInput = "change direction"

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	if um.stageSteer {
		t.Error("expected stageSteer to be cleared after enter")
	}
	if um.steerInput != "" {
		t.Errorf("expected steer input cleared, got '%s'", um.steerInput)
	}
}

func TestFollowupQueueCommand(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.composer.SetValue("/followup do this next")

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	if len(um.followupQueue) != 1 {
		t.Fatalf("expected 1 followup, got %d", len(um.followupQueue))
	}
	if um.followupQueue[0] != "do this next" {
		t.Errorf("expected 'do this next', got '%s'", um.followupQueue[0])
	}
}

func TestPlanModeToggle(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	m = updated.(model)
	m.composer.SetValue("/plan")

	updated, _ = m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	um := updated.(model)

	if !um.planMode {
		t.Error("expected planMode to be true after /plan command")
	}
}

// --- Phase 5: External editor keybinding ---

func TestCtrlEInInputStage(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.composer.SetValue("initial text")

	updated, cmd := m.Update(tea.KeyPressMsg(tea.Key{Code: 'e', Mod: tea.ModCtrl}))
	// The command should trigger openEditorCmd
	if cmd == nil {
		t.Error("expected non-nil command for Ctrl+E (editor)")
	}
	um := updated.(model)
	// Composer content should remain unchanged until editor returns
	if um.composer.Value() != "initial text" {
		t.Errorf("expected composer content preserved, got '%s'", um.composer.Value())
	}
}

// --- Phase 5: Theme detection ---

func TestThemeDetectionDarkDefault(t *testing.T) {
	msg := detectThemeCmd()
	result := msg()
	bgMsg, ok := result.(bgColorMsg)
	if !ok {
		t.Fatalf("expected bgColorMsg, got %T", result)
	}
	// Default (no COLORFGBG) should be dark
	if bgMsg.R != 30 || bgMsg.G != 30 || bgMsg.B != 30 {
		t.Errorf("expected dark default (30,30,30), got (%d,%d,%d)", bgMsg.R, bgMsg.G, bgMsg.B)
	}
}

// --- Phase 5: Frecency history ---

func TestFrecencyAddNewEntry(t *testing.T) {
	var entries []historyEntry
	entries = historyAddFrecency(entries, "hello")
	if len(entries) != 1 {
		t.Fatalf("expected 1 entry, got %d", len(entries))
	}
	if entries[0].Text != "hello" || entries[0].Count != 1 {
		t.Errorf("expected hello/1, got %s/%d", entries[0].Text, entries[0].Count)
	}
}

func TestFrecencyAddExistingEntry(t *testing.T) {
	entries := []historyEntry{{Text: "hello", Count: 3, Last: 1000}}
	entries = historyAddFrecency(entries, "hello")
	if entries[0].Count != 4 {
		t.Errorf("expected count 4, got %d", entries[0].Count)
	}
}

func TestFrecencySortByScore(t *testing.T) {
	entries := []historyEntry{
		{Text: "rare", Count: 1, Last: 100},
		{Text: "frequent", Count: 10, Last: 99999},
	}
	sorted := sortByFrecency(entries)
	if sorted[0].Text != "frequent" {
		t.Errorf("expected 'frequent' first, got '%s'", sorted[0].Text)
	}
}
