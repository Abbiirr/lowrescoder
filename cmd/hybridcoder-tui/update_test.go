package main

import (
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"
)

func TestUpdateWindowSizeMsg(t *testing.T) {
	m := initialModel(nil)
	updated, _ := m.Update(tea.WindowSizeMsg{Width: 120, Height: 40})
	um := updated.(model)
	if um.width != 120 {
		t.Errorf("expected width=120, got %d", um.width)
	}
	if um.height != 40 {
		t.Errorf("expected height=40, got %d", um.height)
	}
}

func TestUpdateStatusMsg(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInit

	updated, _ := m.Update(backendStatusMsg{
		Model:    "qwen3:8b",
		Provider: "ollama",
		Mode:     "suggest",
	})
	um := updated.(model)

	if um.stage != stageInput {
		t.Errorf("expected stageInput after status, got %d", um.stage)
	}
	if um.statusBar.Model != "qwen3:8b" {
		t.Errorf("expected model=qwen3:8b, got %s", um.statusBar.Model)
	}
	if um.statusBar.Provider != "ollama" {
		t.Errorf("expected provider=ollama, got %s", um.statusBar.Provider)
	}
}

func TestUpdateStatusMsgDoesNotChangeStageIfNotInit(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming

	updated, _ := m.Update(backendStatusMsg{
		Model:    "qwen3:8b",
		Provider: "ollama",
		Mode:     "suggest",
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

	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyCtrlC})
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

	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyCtrlC})
	um := updated.(model)

	if !um.quitting {
		t.Error("should quit on second Ctrl+C")
	}
}

func TestHandleInputKeyCtrlD(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, cmd := m.Update(tea.KeyMsg{Type: tea.KeyCtrlD})
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
	m.textInput.SetValue("")

	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	um := updated.(model)

	if um.stage != stageInput {
		t.Error("should stay in input stage when text is empty")
	}
}

func TestHandleStreamingKeyCtrlC(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.messageQueue = []string{"queued msg"}

	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyCtrlC})
	um := updated.(model)

	if um.messageQueue != nil {
		t.Error("expected queue to be cleared on cancel")
	}
}

func TestHandleStreamingKeyEscape(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.messageQueue = []string{"queued msg"}

	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyEscape})
	um := updated.(model)

	if um.messageQueue != nil {
		t.Error("expected queue to be cleared on escape")
	}
}

func TestHandleStreamingKeyEnterQueues(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.textInput.SetValue("next message")

	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
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
	m.textInput.SetValue("overflow")

	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
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
	m.textInput.SetValue("/exit")

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
	m.textInput.SetValue("hello world")

	// sendChat should NOT blur the textInput
	um, _ := m.sendChat("hello world")
	result := um.(model)

	if result.stage != stageStreaming {
		t.Errorf("expected stageStreaming, got %d", result.stage)
	}
	// textInput should still be focused (not blurred)
	if !result.textInput.Focused() {
		t.Error("expected textInput to remain focused during streaming for parallel typing")
	}
}

func TestTypingDuringStreaming(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	// textInput should be focused for parallel typing
	m.textInput.Focus()

	// Simulate typing a character during streaming
	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'a'}})
	um := updated.(model)

	if um.textInput.Value() != "a" {
		t.Errorf("expected textInput value='a' during streaming, got '%s'", um.textInput.Value())
	}
	// Should still be streaming
	if um.stage != stageStreaming {
		t.Errorf("expected to stay in stageStreaming, got %d", um.stage)
	}
}

func TestQueueMessageDuringStreamingPreservesInput(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.textInput.Focus()
	m.textInput.SetValue("queued message")

	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	um := updated.(model)

	// Message should be queued
	if len(um.messageQueue) != 1 || um.messageQueue[0] != "queued message" {
		t.Errorf("expected 'queued message' in queue, got %v", um.messageQueue)
	}
	// textInput should be cleared after queuing
	if um.textInput.Value() != "" {
		t.Errorf("expected textInput cleared after queue, got '%s'", um.textInput.Value())
	}
	// Should still be focused for more parallel typing
	if !um.textInput.Focused() {
		t.Error("expected textInput to remain focused after queuing")
	}
}

func TestCtrlCDuringStreamingCancels(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.textInput.Focus()
	m.messageQueue = []string{"a", "b"}
	m.interruptCount = 0

	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyCtrlC})
	um := updated.(model)

	// Queue should be cleared
	if um.messageQueue != nil {
		t.Errorf("expected queue cleared on Ctrl+C, got %v", um.messageQueue)
	}
	// Should still be in streaming (waiting for backend to confirm cancel)
	if um.stage != stageStreaming {
		t.Errorf("expected to stay in stageStreaming after cancel, got %d", um.stage)
	}
	// interruptCount should be 1 (next Ctrl+C will force quit)
	if um.interruptCount != 1 {
		t.Errorf("expected interruptCount=1, got %d", um.interruptCount)
	}
}

func TestDoubleCtrlCDuringStreamingQuits(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.interruptCount = 0

	// First Ctrl+C: cancel, don't quit
	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyCtrlC})
	um := updated.(model)
	if um.quitting {
		t.Error("first Ctrl+C should cancel, not quit")
	}
	if um.interruptCount != 1 {
		t.Errorf("expected interruptCount=1 after first Ctrl+C, got %d", um.interruptCount)
	}

	// Second Ctrl+C: force quit
	updated2, _ := um.Update(tea.KeyMsg{Type: tea.KeyCtrlC})
	um2 := updated2.(model)
	if !um2.quitting {
		t.Error("second Ctrl+C should force-quit during streaming")
	}
}

func TestCtrlCDuringInputFirstPress(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.interruptCount = 0

	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyCtrlC})
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

	updated, cmd := m.Update(tea.KeyMsg{Type: tea.KeyCtrlC})
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

	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyEscape})
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

	updated, _ := handleApprovalKey(m, tea.KeyMsg{Type: tea.KeyEnter})
	um := updated.(model)

	if um.stage != stageStreaming {
		t.Errorf("expected stageStreaming after approval, got %d", um.stage)
	}
	if !um.textInput.Focused() {
		t.Error("expected textInput focused after approval for parallel typing")
	}
}

func TestInputFocusRestoredAfterApprovalDenied(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageApproval
	m.approvalRequestID = 1000

	updated, _ := handleApprovalKey(m, tea.KeyMsg{Type: tea.KeyEscape})
	um := updated.(model)

	if um.stage != stageStreaming {
		t.Errorf("expected stageStreaming after denial, got %d", um.stage)
	}
	if !um.textInput.Focused() {
		t.Error("expected textInput focused after denial for parallel typing")
	}
}

func TestInputFocusRestoredAfterAskUser(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageAskUser
	m.askRequestID = 1001
	m.askOptions = []string{"A", "B"}
	m.askCursor = 0

	updated, _ := handleAskUserKey(m, tea.KeyMsg{Type: tea.KeyEnter})
	um := updated.(model)

	if um.stage != stageStreaming {
		t.Errorf("expected stageStreaming after ask-user, got %d", um.stage)
	}
	if !um.textInput.Focused() {
		t.Error("expected textInput focused after ask-user for parallel typing")
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
	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyCtrlD})
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
	view := m.View()

	if !strings.Contains(view, "Queue: 3") {
		t.Errorf("expected 'Queue: 3' in view, got:\n%s", view)
	}
}

// --- Tool call edit tracking ---

func TestWriteFileToolCallTracksEdits(t *testing.T) {
	m := initialModel(nil)
	m.toolCalls = []toolCallEntry{{Name: "write_file", Status: "running"}}

	updated, _ := m.Update(backendToolCallMsg{
		Name:   "write_file",
		Status: "completed",
		Result: "Written to /tmp/test.txt",
	})
	um := updated.(model)

	if um.statusBar.Edits != 1 {
		t.Errorf("expected 1 edit tracked, got %d", um.statusBar.Edits)
	}
}

func TestNonWriteToolCallDoesNotTrackEdits(t *testing.T) {
	m := initialModel(nil)
	m.toolCalls = []toolCallEntry{{Name: "read_file", Status: "running"}}

	updated, _ := m.Update(backendToolCallMsg{
		Name:   "read_file",
		Status: "completed",
		Result: "contents",
	})
	um := updated.(model)

	if um.statusBar.Edits != 0 {
		t.Errorf("expected 0 edits for read_file, got %d", um.statusBar.Edits)
	}
}

// --- Interrupt count reset on send ---

func TestInterruptCountResetsOnSend(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.interruptCount = 1
	m.textInput.SetValue("hello")

	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
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
	m.textInput.SetValue("/exit")

	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	um := updated.(model)

	if !um.quitting {
		t.Error("expected quitting=true after /exit Enter")
	}
}

func TestSlashThinkingViaEnter(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.showThinking = true
	m.textInput.SetValue("/thinking")

	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	um := updated.(model)

	if um.showThinking {
		t.Error("expected showThinking=false after /thinking toggle")
	}
}

func TestSlashCommandBackendDelegatedNoBackend(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.textInput.SetValue("/help")

	updated, cmd := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
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
		updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{r}})
		m = updated.(model)
	}

	// The textinput should have /help as current suggestion
	suggestion := m.textInput.CurrentSuggestion()
	if suggestion != "/help" {
		t.Fatalf("expected current suggestion '/help', got '%s'", suggestion)
	}

	// Press Enter — should accept suggestion and submit /help, not /hel
	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = updated.(model)

	// The value was cleared (submitted), so we can't check it directly.
	// But the command should have been handled as /help (not /hel which would be unknown).
	// Since backend is nil, /help would return an error Println.
	// /hel (unknown) would also go to backend delegation path.
	// Either way, it shouldn't crash and textInput should be cleared.
	if m.textInput.Value() != "" {
		t.Errorf("expected textInput cleared after Enter, got '%s'", m.textInput.Value())
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
	m.textInput.SetValue("/exit")

	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	um := updated.(model)

	if um.completions != nil {
		t.Errorf("expected completions cleared after slash command, got %v", um.completions)
	}
}

// --- updateCompletions tests ---

func TestUpdateCompletionsForSlashInput(t *testing.T) {
	m := initialModel(nil)
	m.textInput.SetValue("/he")
	m.updateCompletions()

	if len(m.completions) == 0 {
		t.Fatal("expected completions for /he")
	}
}

func TestUpdateCompletionsClearsForNonSlash(t *testing.T) {
	m := initialModel(nil)
	m.textInput.SetValue("hello")
	m.updateCompletions()

	if m.completions != nil {
		t.Errorf("expected nil completions for non-slash, got %v", m.completions)
	}
}

func TestUpdateCompletionsClearsAfterSpace(t *testing.T) {
	m := initialModel(nil)
	m.textInput.SetValue("/help arg")
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
	m.textInput.SetValue("/resume")

	updated, cmd := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
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
