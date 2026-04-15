package main

import (
	"strings"
	"testing"
	"time"

	tea "charm.land/bubbletea/v2"
)

// e2e tests simulate full message flows through the Update loop.
// Each test creates initialModel(nil), feeds tea.Msg sequences, and verifies state.

func TestFullChatFlow(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80

	// Step 1: User sends a message
	m.composer.SetValue("hello world")
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
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
	view := m.View().Content
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
	m.composer.SetValue("read the file")
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
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
	view := m.View().Content
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
	m.composer.SetValue("write a file")
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
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

	// View shows approval prompt (title-cased tool name)
	view := m.View().Content
	if !strings.Contains(view, "Write File") {
		t.Errorf("expected approval prompt (Write File) in view, got:\n%s", view)
	}
	if !strings.Contains(view, "Yes") {
		t.Errorf("expected approval options in view")
	}

	// User approves (Enter on first option "Yes")
	m.approvalCursor = 0
	updated, _ = handleApprovalKey(m, tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	m = updated.(model)

	if m.stage != stageStreaming {
		t.Errorf("expected stageStreaming after approval, got %d", m.stage)
	}
	if !m.composer.Focused() {
		t.Error("expected composer focused after approval")
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
	m.composer.SetValue("do something")
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	m = updated.(model)

	// Queue another message while streaming
	m.composer.SetValue("next task")
	updated, _ = m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	m = updated.(model)
	if len(m.messageQueue) != 1 {
		t.Fatalf("expected 1 queued message, got %d", len(m.messageQueue))
	}

	// Cancel with Escape (Ctrl+C enters steer mode; Esc cancels)
	updated, _ = m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEscape}))
	m = updated.(model)

	// Queue should be cleared
	if m.messageQueue != nil {
		t.Errorf("expected queue cleared after cancel, got %v", m.messageQueue)
	}
	// Still streaming (waiting for backend to confirm cancel)
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
	m.composer.SetValue("first")
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	m = updated.(model)

	// Type and queue second message during streaming
	m.composer.SetValue("second")
	updated, _ = m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
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

func TestFullSessionResumeFlow(t *testing.T) {
	b := NewBackend()
	m := initialModel(b)
	m.stage = stageInput
	m.width = 80

	// Step 1: User types /resume and presses Enter
	m.composer.SetValue("/resume")
	updated, cmd := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	m = updated.(model)

	// Should have sent session.list to backend
	select {
	case data := <-b.writeCh:
		if !strings.Contains(string(data), "session.list") {
			t.Fatalf("expected session.list RPC, got %s", string(data))
		}
	default:
		t.Fatal("expected session.list message in writeCh")
	}

	// The cmd is a blocking tea.Cmd that waits for the response.
	// We can't easily execute it in tests, so we simulate the result directly.
	if cmd == nil {
		t.Fatal("expected non-nil cmd from /resume")
	}

	// Step 2: Simulate backendSessionListMsg arriving
	sessions := []sessionEntry{
		{ID: "session-aaa-111", Title: "First project", Model: "qwen3:8b", Provider: "ollama"},
		{ID: "session-bbb-222", Title: "Second project", Model: "gpt-4", Provider: "openrouter"},
		{ID: "session-ccc-333", Title: "Third project", Model: "llama3", Provider: "ollama"},
	}
	updated, _ = m.Update(backendSessionListMsg{Sessions: sessions})
	m = updated.(model)

	if m.stage != stageAskUser {
		t.Fatalf("expected stageAskUser, got %d", m.stage)
	}
	if m.askRequestID != -1 {
		t.Fatalf("expected sentinel askRequestID=-1, got %d", m.askRequestID)
	}
	if len(m.askOptions) != 3 {
		t.Fatalf("expected 3 options, got %d", len(m.askOptions))
	}

	// Verify view shows the picker
	view := m.View().Content
	if !strings.Contains(view, "Select a session to resume") {
		t.Errorf("expected question in view")
	}
	if !strings.Contains(view, "First project") {
		t.Errorf("expected session title in view")
	}

	// Step 3: Navigate to second item
	updated, _ = m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyDown}))
	m = updated.(model)
	if m.askCursor != 1 {
		t.Errorf("expected cursor=1, got %d", m.askCursor)
	}

	// Step 4: Select second item
	updated, cmd = m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	m = updated.(model)

	if m.stage != stageInput {
		t.Errorf("expected stageInput after selection, got %d", m.stage)
	}
	if m.sessionPickerEntries != nil {
		t.Error("expected sessionPickerEntries cleared")
	}
	if !m.composer.Focused() {
		t.Error("expected composer focused")
	}

	// Should have sent session.resume with the full ID of second session
	select {
	case data := <-b.writeCh:
		s := string(data)
		if !strings.Contains(s, "session.resume") {
			t.Errorf("expected session.resume, got %s", s)
		}
		if !strings.Contains(s, "session-bbb-222") {
			t.Errorf("expected session-bbb-222 in request, got %s", s)
		}
	default:
		t.Error("expected session.resume message")
	}

	// Should return a confirmation Println
	if cmd == nil {
		t.Error("expected confirmation Println command")
	}
}

func TestFullSessionResumeCancelFlow(t *testing.T) {
	b := NewBackend()
	m := initialModel(b)
	m.stage = stageInput
	m.width = 80

	// Step 1: Simulate session list arriving (skip the /resume typing)
	sessions := []sessionEntry{
		{ID: "id1", Title: "Session 1", Model: "m1"},
		{ID: "id2", Title: "Session 2", Model: "m2"},
	}
	updated, _ := m.Update(backendSessionListMsg{Sessions: sessions})
	m = updated.(model)

	if m.stage != stageAskUser {
		t.Fatalf("expected stageAskUser, got %d", m.stage)
	}

	// Step 2: Navigate down
	updated, _ = m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyDown}))
	m = updated.(model)
	if m.askCursor != 1 {
		t.Errorf("expected cursor=1, got %d", m.askCursor)
	}

	// Step 3: Cancel with Escape
	updated, cmd := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEscape}))
	m = updated.(model)

	if m.stage != stageInput {
		t.Errorf("expected stageInput after cancel, got %d", m.stage)
	}
	if m.sessionPickerEntries != nil {
		t.Error("expected sessionPickerEntries cleared after cancel")
	}
	if !m.composer.Focused() {
		t.Error("expected composer focused after cancel")
	}

	// Should NOT have sent any message to the backend (no session.resume, no AskUserResult)
	select {
	case data := <-b.writeCh:
		t.Errorf("expected no backend message on cancel, but got: %s", string(data))
	default:
		// Good — nothing sent
	}

	if cmd == nil {
		t.Error("expected cancel confirmation Println")
	}

	// Step 4: Can now type normally
	m.composer.SetValue("hello after cancel")
	updated, _ = m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	m = updated.(model)

	if m.stage != stageStreaming {
		t.Errorf("expected stageStreaming after normal chat, got %d", m.stage)
	}
}

func TestFullSessionResumeDirectIDFlow(t *testing.T) {
	b := NewBackend()
	m := initialModel(b)
	m.stage = stageInput
	m.width = 80

	// Type /resume with a direct session ID
	m.composer.SetValue("/resume my-session-id")
	updated, cmd := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	m = updated.(model)

	// Should NOT enter session picker — should go directly to resume
	if m.stage == stageAskUser {
		t.Error("should not enter session picker when ID is given")
	}

	// Should have sent session.resume directly
	select {
	case data := <-b.writeCh:
		s := string(data)
		if !strings.Contains(s, "session.resume") {
			t.Errorf("expected session.resume, got %s", s)
		}
		if !strings.Contains(s, "my-session-id") {
			t.Errorf("expected my-session-id, got %s", s)
		}
	default:
		t.Error("expected session.resume message")
	}

	if cmd == nil {
		t.Error("expected confirmation Println")
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
	m.composer.SetValue("explain this")
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
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
	view := m.View().Content
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

func TestFullThinkingTokensDisplayInRealTime(t *testing.T) {
	// Simulates a long reasoning chain arriving token-by-token and verifies
	// that each chunk is visible in View() immediately — not just after done.
	// Prompt: "think long and hard, two people sitting under a tree, what is
	//          the probability it is an apple tree if they are in england"
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 100

	if !m.showThinking {
		t.Fatal("showThinking should default to true")
	}

	// User sends the prompt
	m.composer.SetValue("think long and hard, two people sitting under a tree, what is the probability it is an apple tree if they are in england")
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	m = updated.(model)

	if m.stage != stageStreaming {
		t.Fatalf("expected stageStreaming, got %d", m.stage)
	}

	// --- Simulate thinking tokens arriving one chunk at a time ---
	// Each chunk represents what the LLM's <think> block emits incrementally.

	thinkingChunks := []string{
		"Let me think about this step by step.\n\n",
		"First, I need to consider what types of trees are common in England.\n",
		"England has a temperate maritime climate, so common trees include:\n",
		"- Oak (Quercus robur) — the most common broadleaf\n",
		"- Ash, Beech, Birch, Sycamore, Horse Chestnut\n",
		"- Apple trees (Malus domestica) — found in orchards and gardens\n\n",
		"According to the Forestry Commission, there are roughly 3.2 billion trees in the UK.\n",
		"Apple trees are primarily found in orchards (Kent, Herefordshire, Somerset).\n",
		"Estimated apple trees: ~10-15 million in commercial orchards,\n",
		"plus perhaps 5-10 million in domestic gardens.\n\n",
		"So roughly 15-25 million apple trees out of ~3.2 billion total.\n",
		"That gives a probability of about 0.5-0.8%.\n\n",
		"But wait — the question says \"two people sitting under a tree.\" ",
		"People sit under large, shade-giving trees. Apple trees are typically small.\n",
		"This biases AGAINST apple trees. The most likely candidates for sitting under:\n",
		"Oak, Beech, or Sycamore — all large canopy trees.\n\n",
		"Adjusting for the sitting-under bias, I'd estimate the probability drops to 0.1-0.3%.",
	}

	// Deliver each chunk and verify it appears in the view IMMEDIATELY
	for i, chunk := range thinkingChunks {
		updated, cmd := m.Update(backendThinkingMsg{Text: chunk})
		m = updated.(model)

		// First chunk should trigger a tick (streamDirty)
		if i == 0 && cmd == nil {
			t.Error("expected tickCmd on first thinking token")
		}

		// The thinkingBuf should contain all chunks delivered so far
		expectedSoFar := ""
		for j := 0; j <= i; j++ {
			expectedSoFar += thinkingChunks[j]
		}
		if m.thinkingBuf.String() != expectedSoFar {
			t.Errorf("chunk %d: thinkingBuf mismatch.\nExpected len=%d, got len=%d",
				i, len(expectedSoFar), m.thinkingBuf.Len())
		}

		// View() should show thinking content right now — not deferred to done
		view := m.View().Content
		// The view caps thinking at 5 lines, so check the latest chunk
		// is visible (at least the tail of what's been delivered)
		if i < 3 {
			// First few chunks: the first line is still within the 5-line cap
			if !strings.Contains(view, "think about this") {
				t.Errorf("chunk %d: first thinking line not visible in view", i)
			}
		}
		// The most recent line should always be visible (it's in the last 5)
		lastLine := strings.TrimSpace(chunk)
		if lastLine != "" {
			// Extract just the first few words to check
			words := strings.Fields(lastLine)
			if len(words) > 3 {
				searchTerm := strings.Join(words[:3], " ")
				if !strings.Contains(view, searchTerm) {
					t.Errorf("chunk %d: latest thinking not visible in view.\nSearched for: '%s'\nView:\n%s",
						i, searchTerm, view)
				}
			}
		}
	}

	// Verify the 5-line cap is working — with 17 chunks containing many newlines,
	// the view should NOT show all lines
	fullThinking := m.thinkingBuf.String()
	allLines := strings.Split(fullThinking, "\n")
	view := m.View().Content
	visibleLineCount := 0
	for _, line := range allLines {
		trimmed := strings.TrimSpace(line)
		if trimmed != "" && strings.Contains(view, trimmed) {
			visibleLineCount++
		}
	}
	// With the 5-line cap, at most ~5 lines should be visible
	if visibleLineCount > 7 { // allow some slack for partial matches
		t.Errorf("expected at most ~5 visible thinking lines (cap), got %d visible", visibleLineCount)
	}

	// --- Now regular response tokens arrive alongside thinking ---
	updated, _ = m.Update(backendTokenMsg{Text: "Based on my analysis, the probability"})
	m = updated.(model)
	updated, _ = m.Update(backendTokenMsg{Text: " of it being an apple tree is approximately 0.1-0.3%."})
	m = updated.(model)

	// Tick to flush tokens
	updated, _ = m.Update(tickMsg{Time: time.Now()})
	m = updated.(model)

	// View should show BOTH thinking AND streaming response
	view = m.View().Content
	if !strings.Contains(view, "probability drops") {
		t.Error("expected thinking content still visible while response streams")
	}
	if !strings.Contains(view, "approximately 0.1-0.3%") {
		t.Errorf("expected response tokens in view during streaming, got:\n%s", view)
	}

	// --- Done arrives ---
	updated, cmd := m.Update(backendDoneMsg{TokensIn: 200, TokensOut: 500})
	m = updated.(model)

	if m.stage != stageInput {
		t.Errorf("expected stageInput after done, got %d", m.stage)
	}
	// Thinking should be cleared after done
	if m.thinkingBuf.Len() != 0 {
		t.Error("expected thinkingBuf reset after done")
	}
	// Stream buffer should be cleared (content committed via tea.Println)
	if m.streamBuf.Len() != 0 {
		t.Error("expected streamBuf reset after done")
	}
	// Done should return a command batch (Println for content + separator)
	if cmd == nil {
		t.Error("expected non-nil command from handleDone")
	}

	// View should no longer show thinking (it was reset)
	view = m.View().Content
	if strings.Contains(view, "apple trees") {
		t.Error("expected thinking content gone from view after done")
	}
}

func TestThinkingTokensDisabledNotShownInView(t *testing.T) {
	// When showThinking is toggled off, thinking tokens should still accumulate
	// (so they're not lost) but NOT appear in the View().
	m := initialModel(nil)
	m.stage = stageStreaming
	m.width = 80

	// Toggle thinking off
	m.showThinking = false

	// Deliver thinking tokens
	updated, _ := m.Update(backendThinkingMsg{Text: "secret reasoning about apple trees in England"})
	m = updated.(model)

	// Buffer should accumulate (not lost)
	if m.thinkingBuf.String() != "secret reasoning about apple trees in England" {
		t.Errorf("expected thinking to accumulate even when hidden, got '%s'", m.thinkingBuf.String())
	}

	// But View should NOT show it
	view := m.View().Content
	if strings.Contains(view, "secret reasoning") {
		t.Error("expected thinking hidden when showThinking=false")
	}

	// Toggle back on — thinking should now appear
	m.showThinking = true
	view = m.View().Content
	if !strings.Contains(view, "secret reasoning") {
		t.Errorf("expected thinking visible after re-enabling, got:\n%s", view)
	}
}

func TestThinkingTokensInterleavedWithResponseTokens(t *testing.T) {
	// Tests the realistic scenario where thinking and response tokens
	// arrive in an interleaved pattern (as happens with some models).
	m := initialModel(nil)
	m.stage = stageStreaming
	m.width = 80

	// Thinking token arrives
	updated, _ := m.Update(backendThinkingMsg{Text: "Considering tree species distribution..."})
	m = updated.(model)

	// Response token arrives (this can happen when thinking ends and response begins)
	updated, _ = m.Update(backendTokenMsg{Text: "The probability "})
	m = updated.(model)

	// More thinking (some models interleave)
	updated, _ = m.Update(backendThinkingMsg{Text: "\nActually let me reconsider the climate factor."})
	m = updated.(model)

	// More response
	updated, _ = m.Update(backendTokenMsg{Text: "is approximately "})
	m = updated.(model)

	// Tick to flush response tokens
	updated, _ = m.Update(tickMsg{Time: time.Now()})
	m = updated.(model)

	// Thinking should have both chunks
	expectedThinking := "Considering tree species distribution...\nActually let me reconsider the climate factor."
	if m.thinkingBuf.String() != expectedThinking {
		t.Errorf("thinking mismatch.\nExpected: %s\nGot: %s", expectedThinking, m.thinkingBuf.String())
	}

	// Response should have both chunks
	if m.streamBuf.String() != "The probability is approximately " {
		t.Errorf("response mismatch.\nExpected: 'The probability is approximately '\nGot: '%s'", m.streamBuf.String())
	}

	// View should show both thinking and streaming content
	view := m.View().Content
	if !strings.Contains(view, "reconsider the climate") {
		t.Errorf("expected thinking in view, got:\n%s", view)
	}
	if !strings.Contains(view, "approximately") {
		t.Errorf("expected response in view, got:\n%s", view)
	}
}
