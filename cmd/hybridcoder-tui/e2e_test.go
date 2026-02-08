package main

import (
	"strings"
	"testing"
	"time"

	tea "github.com/charmbracelet/bubbletea"
)

// e2e tests simulate full message flows through the Update loop.
// Each test creates initialModel(nil), feeds tea.Msg sequences, and verifies state.

func TestFullChatFlow(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80

	// Step 1: User sends a message
	m.textInput.SetValue("hello world")
	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = updated.(model)

	if m.stage != stageStreaming {
		t.Fatalf("expected stageStreaming after send, got %d", m.stage)
	}
	if m.streamBuf.Len() != 0 {
		t.Error("expected empty streamBuf at start of streaming")
	}

	// Step 2: Tokens arrive
	updated, cmd := m.Update(backendTokenMsg{Text: "Hi "})
	m = updated.(model)
	if m.tokenBuf.String() != "Hi " {
		t.Errorf("expected tokenBuf='Hi ', got '%s'", m.tokenBuf.String())
	}
	if cmd == nil {
		t.Error("expected tickCmd to be returned")
	}

	// Step 3: More tokens (no duplicate tick)
	updated, cmd = m.Update(backendTokenMsg{Text: "there!"})
	m = updated.(model)
	if m.tokenBuf.String() != "Hi there!" {
		t.Errorf("expected tokenBuf='Hi there!', got '%s'", m.tokenBuf.String())
	}
	if cmd != nil {
		t.Error("expected no duplicate tick when streamDirty already true")
	}

	// Step 4: Tick fires — flush to streamBuf
	updated, _ = m.Update(tickMsg{Time: time.Now()})
	m = updated.(model)
	if m.streamBuf.String() != "Hi there!" {
		t.Errorf("expected streamBuf='Hi there!' after tick, got '%s'", m.streamBuf.String())
	}
	if m.tokenBuf.Len() != 0 {
		t.Error("expected tokenBuf empty after tick")
	}

	// Step 5: Verify View shows content during streaming
	view := m.View()
	if !strings.Contains(view, "Hi there!") {
		t.Errorf("expected streaming content in View, got:\n%s", view)
	}

	// Step 6: Done arrives
	updated, cmd = m.Update(backendDoneMsg{TokensIn: 10, TokensOut: 20})
	m = updated.(model)

	if m.stage != stageInput {
		t.Errorf("expected stageInput after done, got %d", m.stage)
	}
	if m.streamBuf.Len() != 0 {
		t.Error("expected streamBuf reset after done")
	}
	// Should have returned a batch of commands (tea.Println for content + separator)
	if cmd == nil {
		t.Error("expected non-nil command batch from handleDone")
	}
}

func TestFullChatFlowWithToolCall(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	// Send message
	m.textInput.SetValue("read the file")
	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = updated.(model)

	// Tool call starts
	updated, _ = m.Update(backendToolCallMsg{Name: "read_file", Status: "running", Args: "/tmp/test.txt"})
	m = updated.(model)
	if len(m.toolCalls) != 1 {
		t.Fatalf("expected 1 tool call, got %d", len(m.toolCalls))
	}
	if m.toolCalls[0].Status != "running" {
		t.Errorf("expected status=running, got %s", m.toolCalls[0].Status)
	}

	// View should show tool call
	view := m.View()
	if !strings.Contains(view, "read_file") {
		t.Errorf("expected tool call in view during streaming")
	}

	// Tool call completes
	updated, _ = m.Update(backendToolCallMsg{Name: "read_file", Status: "completed", Result: "file contents"})
	m = updated.(model)
	if m.toolCalls[0].Status != "completed" {
		t.Errorf("expected status=completed, got %s", m.toolCalls[0].Status)
	}

	// Tokens arrive
	updated, _ = m.Update(backendTokenMsg{Text: "The file contains..."})
	m = updated.(model)

	// Tick
	updated, _ = m.Update(tickMsg{Time: time.Now()})
	m = updated.(model)

	// Done
	updated, cmd := m.Update(backendDoneMsg{TokensIn: 50, TokensOut: 100})
	m = updated.(model)

	if m.stage != stageInput {
		t.Errorf("expected stageInput after done, got %d", m.stage)
	}
	if cmd == nil {
		t.Error("expected non-nil command batch")
	}
}

func TestFullApprovalFlow(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	// Send message
	m.textInput.SetValue("write a file")
	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = updated.(model)

	// Some tokens
	updated, _ = m.Update(backendTokenMsg{Text: "I'll write "})
	m = updated.(model)
	updated, _ = m.Update(tickMsg{Time: time.Now()})
	m = updated.(model)

	// Approval request arrives
	updated, _ = m.Update(backendApprovalRequestMsg{
		RequestID: 500,
		Tool:      "write_file",
		Args:      `{"path": "/tmp/out.txt"}`,
	})
	m = updated.(model)

	if m.stage != stageApproval {
		t.Fatalf("expected stageApproval, got %d", m.stage)
	}

	// View shows approval prompt
	view := m.View()
	if !strings.Contains(view, "write_file") {
		t.Errorf("expected approval prompt in view")
	}
	if !strings.Contains(view, "Yes") {
		t.Errorf("expected approval options in view")
	}

	// User approves (Enter on first option "Yes")
	m.approvalCursor = 0
	updated, _ = handleApprovalKey(m, tea.KeyMsg{Type: tea.KeyEnter})
	m = updated.(model)

	if m.stage != stageStreaming {
		t.Errorf("expected stageStreaming after approval, got %d", m.stage)
	}
	if !m.textInput.Focused() {
		t.Error("expected textInput focused after approval")
	}

	// More tokens and done
	updated, _ = m.Update(backendTokenMsg{Text: "Done writing."})
	m = updated.(model)
	updated, _ = m.Update(tickMsg{Time: time.Now()})
	m = updated.(model)
	updated, _ = m.Update(backendDoneMsg{TokensIn: 30, TokensOut: 60})
	m = updated.(model)

	if m.stage != stageInput {
		t.Errorf("expected stageInput after done, got %d", m.stage)
	}
}

func TestFullCancelFlow(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	// Send message
	m.textInput.SetValue("do something")
	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = updated.(model)

	// Queue another message while streaming
	m.textInput.SetValue("next task")
	updated, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = updated.(model)
	if len(m.messageQueue) != 1 {
		t.Fatalf("expected 1 queued message, got %d", len(m.messageQueue))
	}

	// Cancel with Ctrl+C
	updated, _ = m.Update(tea.KeyMsg{Type: tea.KeyCtrlC})
	m = updated.(model)

	// Queue should be cleared
	if m.messageQueue != nil {
		t.Errorf("expected queue cleared after cancel, got %v", m.messageQueue)
	}
	// Still streaming (waiting for backend done)
	if m.stage != stageStreaming {
		t.Errorf("expected stageStreaming while waiting for cancel confirmation, got %d", m.stage)
	}

	// Backend sends done with cancelled=true
	updated, _ = m.Update(backendDoneMsg{Cancelled: true})
	m = updated.(model)

	if m.stage != stageInput {
		t.Errorf("expected stageInput after cancelled done, got %d", m.stage)
	}
}

func TestFullQueueFlow(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	// Send first message
	m.textInput.SetValue("first")
	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = updated.(model)

	// Type and queue second message during streaming
	m.textInput.SetValue("second")
	updated, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = updated.(model)

	if len(m.messageQueue) != 1 {
		t.Fatalf("expected 1 queued, got %d", len(m.messageQueue))
	}
	if m.messageQueue[0] != "second" {
		t.Errorf("expected queued 'second', got '%s'", m.messageQueue[0])
	}

	// Tokens for first response
	updated, _ = m.Update(backendTokenMsg{Text: "response 1"})
	m = updated.(model)
	updated, _ = m.Update(tickMsg{Time: time.Now()})
	m = updated.(model)

	// Done for first — should trigger queue drain
	updated, cmd := m.Update(backendDoneMsg{TokensIn: 10, TokensOut: 20})
	m = updated.(model)

	if cmd == nil {
		t.Error("expected command batch including queue drain")
	}

	// The queue drain message processes and sends second message
	updated, _ = m.Update(queueDrainMsg{})
	m = updated.(model)

	if m.stage != stageStreaming {
		t.Errorf("expected stageStreaming for queued message, got %d", m.stage)
	}
	if len(m.messageQueue) != 0 {
		t.Errorf("expected queue empty after drain, got %d", len(m.messageQueue))
	}
}

func TestFullThinkingFlow(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	// showThinking is true by default — verify
	if !m.showThinking {
		t.Fatal("expected showThinking=true by default")
	}

	// Send message
	m.textInput.SetValue("explain this")
	updated, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = updated.(model)

	// Thinking tokens arrive
	updated, _ = m.Update(backendThinkingMsg{Text: "Let me think..."})
	m = updated.(model)
	updated, _ = m.Update(backendThinkingMsg{Text: " I need to consider..."})
	m = updated.(model)

	if m.thinkingBuf.String() != "Let me think... I need to consider..." {
		t.Errorf("expected accumulated thinking, got '%s'", m.thinkingBuf.String())
	}

	// View should show thinking tokens
	view := m.View()
	if !strings.Contains(view, "Let me think") {
		t.Errorf("expected thinking tokens in view when enabled, got:\n%s", view)
	}

	// Regular tokens
	updated, _ = m.Update(backendTokenMsg{Text: "Here's the explanation."})
	m = updated.(model)
	updated, _ = m.Update(tickMsg{Time: time.Now()})
	m = updated.(model)

	// Done — thinking should be reset
	updated, _ = m.Update(backendDoneMsg{TokensIn: 40, TokensOut: 80})
	m = updated.(model)

	if m.thinkingBuf.Len() != 0 {
		t.Error("expected thinkingBuf reset after done")
	}
}
