package main

import (
	"strings"
	"testing"
	"time"

	tea "charm.land/bubbletea/v2"
)

// --- Milestone A: Runtime Acceptance Matrix ---
//
// Tests cover the runtime acceptance cases for startup, input routing,
// palette/picker, streaming, resize, inline/alt-screen, crash/recovery,
// warning/error classification, and queue semantics.

// ========== Startup ==========

func TestStartupStatusAfterTimeoutClearsError(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInit

	// Fire timeout first
	updated, _ := m.Update(startupTimeoutMsg{})
	m = updated.(model)
	if m.stage != stageInput {
		t.Fatalf("expected stageInput after timeout, got %d", m.stage)
	}
	if m.lastError == "" {
		t.Error("expected error message after timeout")
	}

	// Now backend connects late — error should clear
	updated, _ = m.Update(backendStatusMsg{Model: "test", Provider: "p", Mode: "suggest"})
	m = updated.(model)
	if m.lastError != "" {
		t.Errorf("expected error cleared after late status, got '%s'", m.lastError)
	}
	if m.stage != stageInput {
		t.Errorf("expected still stageInput, got %d", m.stage)
	}
}

func TestStartupStatusDoesNotOverrideAlreadyConnected(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, _ := m.Update(backendStatusMsg{Model: "test", Provider: "p", Mode: "suggest"})
	m = updated.(model)
	if m.stage != stageInput {
		t.Errorf("status should not change stage when already input, got %d", m.stage)
	}
}

func TestStartupExitDuringInit(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInit

	updated, cmd := m.Update(backendExitMsg{Err: nil})
	m = updated.(model)
	if !m.quitting {
		t.Error("expected quitting=true on backend exit during init")
	}
	if cmd == nil {
		t.Error("expected tea.Quit cmd")
	}
}

func TestStartupViewInitShowsSpinner(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInit
	m.width = 80

	view := m.View().Content
	if !strings.Contains(view, "Connecting to backend") {
		t.Errorf("expected startup spinner text in view, got:\n%s", view)
	}
	if !strings.Contains(view, "AutoCode") {
		t.Errorf("expected header in init view, got:\n%s", view)
	}
}

// ========== Palette (Ctrl+K) ==========

func TestCtrlKEntersPalette(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: 'k', Mod: tea.ModCtrl}))
	m = updated.(model)
	if m.stage != stagePalette {
		t.Errorf("expected stagePalette, got %d", m.stage)
	}
	if m.paletteFilter != "" {
		t.Errorf("expected empty filter, got '%s'", m.paletteFilter)
	}
	if len(m.paletteMatches) == 0 {
		t.Error("expected non-empty palette matches")
	}
}

func TestPaletteEscapeReturnsToInput(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	// Enter palette
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: 'k', Mod: tea.ModCtrl}))
	m = updated.(model)

	// Escape closes
	updated, _ = m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEscape}))
	m = updated.(model)
	if m.stage != stageInput {
		t.Errorf("expected stageInput after palette Escape, got %d", m.stage)
	}
	if !m.composer.Focused() {
		t.Error("expected composer focused after palette close")
	}
}

func TestPaletteCtrlKToggle(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	// Open palette
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: 'k', Mod: tea.ModCtrl}))
	m = updated.(model)
	if m.stage != stagePalette {
		t.Fatalf("expected stagePalette, got %d", m.stage)
	}

	// Ctrl+K again closes it
	updated, _ = m.Update(tea.KeyPressMsg(tea.Key{Code: 'k', Mod: tea.ModCtrl}))
	m = updated.(model)
	if m.stage != stageInput {
		t.Errorf("expected stageInput after Ctrl+K toggle, got %d", m.stage)
	}
}

func TestPaletteEnterSetsComposerAndReturnsToInput(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80

	// Enter palette
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: 'k', Mod: tea.ModCtrl}))
	m = updated.(model)

	// Press Enter to select first match
	updated, _ = m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	m = updated.(model)
	if m.stage != stageInput {
		t.Errorf("expected stageInput after palette Enter, got %d", m.stage)
	}
	if !m.composer.Focused() {
		t.Error("expected composer focused after palette selection")
	}
	// Composer should have the selected command
	val := m.composer.Value()
	if val == "" {
		t.Error("expected non-empty composer value after palette selection")
	}
}

func TestPaletteTypingFilters(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: 'k', Mod: tea.ModCtrl}))
	m = updated.(model)
	initialCount := len(m.paletteMatches)

	// Type "model"
	for _, ch := range "model" {
		updated, _ = m.Update(tea.KeyPressMsg(tea.Key{Text: string(ch), Code: ch}))
		m = updated.(model)
	}
	if m.paletteFilter != "model" {
		t.Errorf("expected filter='model', got '%s'", m.paletteFilter)
	}
	if len(m.paletteMatches) >= initialCount {
		t.Errorf("expected filtered results smaller than %d, got %d", initialCount, len(m.paletteMatches))
	}
}

func TestPaletteBackspaceRemovesFilterChar(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: 'k', Mod: tea.ModCtrl}))
	m = updated.(model)

	// Type "exit"
	for _, ch := range "exit" {
		updated, _ = m.Update(tea.KeyPressMsg(tea.Key{Text: string(ch), Code: ch}))
		m = updated.(model)
	}
	if m.paletteFilter != "exit" {
		t.Fatalf("expected filter='exit', got '%s'", m.paletteFilter)
	}

	// Backspace
	updated, _ = m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyBackspace}))
	m = updated.(model)
	if m.paletteFilter != "exi" {
		t.Errorf("expected filter='exi', got '%s'", m.paletteFilter)
	}
}

func TestPaletteArrowNavigation(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: 'k', Mod: tea.ModCtrl}))
	m = updated.(model)
	if m.paletteCursor != 0 {
		t.Fatalf("expected initial cursor=0, got %d", m.paletteCursor)
	}

	// Down
	updated, _ = m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyDown}))
	m = updated.(model)
	if m.paletteCursor != 1 {
		t.Errorf("expected cursor=1 after down, got %d", m.paletteCursor)
	}

	// Up
	updated, _ = m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyUp}))
	m = updated.(model)
	if m.paletteCursor != 0 {
		t.Errorf("expected cursor=0 after up, got %d", m.paletteCursor)
	}
}

func TestPaletteViewRendersCorrectly(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: 'k', Mod: tea.ModCtrl}))
	m = updated.(model)

	view := m.View().Content
	if !strings.Contains(view, "Command Palette") {
		t.Errorf("expected palette header in view, got:\n%s", view)
	}
	if !strings.Contains(view, "type to filter") {
		t.Errorf("expected filter hint in view")
	}
}

// ========== Inline Mode (AltScreen) ==========

func TestViewAltScreenDefaultMode(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80
	m.inlineMode = false

	v := m.View()
	if !v.AltScreen {
		t.Error("expected AltScreen=true in default mode")
	}
}

func TestViewInlineModeNoAltScreen(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80
	m.inlineMode = true

	v := m.View()
	if v.AltScreen {
		t.Error("expected AltScreen=false in inline mode")
	}
}

func TestViewMouseModeAlwaysEnabled(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80

	v := m.View()
	if v.MouseMode != tea.MouseModeCellMotion {
		t.Error("expected MouseModeCellMotion")
	}
}

// ========== Warning vs Error Classification ==========

func TestWarningMsgRendersDimNotError(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80

	updated, cmd := m.Update(backendWarningMsg{Message: "something happened"})
	m = updated.(model)

	// Warning should NOT set lastError
	if m.lastError != "" {
		t.Errorf("expected lastError empty after warning, got '%s'", m.lastError)
	}
	// Warning should return a tea.Println command
	if cmd == nil {
		t.Error("expected Println cmd for warning")
	}
}

func TestErrorMsgSetsLastError(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80

	updated, _ := m.Update(backendErrorMsg{Message: "fatal issue"})
	m = updated.(model)
	if m.lastError != "fatal issue" {
		t.Errorf("expected lastError='fatal issue', got '%s'", m.lastError)
	}
}

func TestWarningDoesNotBreakDuringStreaming(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.width = 80

	updated, _ := m.Update(backendWarningMsg{Message: "rate limit approaching"})
	m = updated.(model)
	if m.stage != stageStreaming {
		t.Errorf("warning should not change streaming stage, got %d", m.stage)
	}
	if m.lastError != "" {
		t.Errorf("warning should not set lastError during streaming, got '%s'", m.lastError)
	}
}

// ========== Backend Death / Crash Recovery ==========

func TestBackendExitDuringStreaming(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.width = 80
	m.tokenBuf.WriteString("partial content")

	updated, cmd := m.Update(backendExitMsg{Err: nil})
	m = updated.(model)
	if !m.quitting {
		t.Error("expected quitting=true on backend exit during streaming")
	}
	if cmd == nil {
		t.Error("expected tea.Quit cmd")
	}
}

func TestBackendExitDuringApproval(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageApproval
	m.approvalRequestID = 42
	m.approvalTool = "write_file"
	m.approvalOptions = []string{"Yes", "No"}

	updated, cmd := m.Update(backendExitMsg{Err: nil})
	m = updated.(model)
	if !m.quitting {
		t.Error("expected quitting=true on backend exit during approval")
	}
	_ = cmd
}

func TestBackendExitDuringAskUser(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageAskUser
	m.askRequestID = 99
	m.askQuestion = "Which file?"

	updated, _ := m.Update(backendExitMsg{Err: nil})
	m = updated.(model)
	if !m.quitting {
		t.Error("expected quitting=true on backend exit during ask-user")
	}
}

func TestBackendExitDuringModelPicker(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageModelPicker
	m.modelPickerEntries = []string{"model-a", "model-b"}

	updated, _ := m.Update(backendExitMsg{Err: nil})
	m = updated.(model)
	if !m.quitting {
		t.Error("expected quitting=true on backend exit during model picker")
	}
}

func TestBackendExitDuringPalette(t *testing.T) {
	m := initialModel(nil)
	m.stage = stagePalette

	updated, _ := m.Update(backendExitMsg{Err: nil})
	m = updated.(model)
	if !m.quitting {
		t.Error("expected quitting=true on backend exit during palette")
	}
}

// ========== Cost / Session-ID / Fork Updates ==========

func TestBackendCostMsgUpdatesTotalCost(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.totalTokensIn = 100
	m.totalTokensOut = 200

	updated, _ := m.Update(backendCostMsg{Cost: "$0.42"})
	m = updated.(model)
	if m.totalCost != "$0.42" {
		t.Errorf("expected totalCost='$0.42', got '%s'", m.totalCost)
	}
	if m.statusBar.Tokens != 300 {
		t.Errorf("expected statusBar.Tokens=300, got %d", m.statusBar.Tokens)
	}
}

func TestBackendSessionIDMsgUpdatesSessionID(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, _ := m.Update(backendSessionIDMsg{SessionID: "abc123"})
	m = updated.(model)
	if m.sessionID != "abc123" {
		t.Errorf("expected sessionID='abc123', got '%s'", m.sessionID)
	}
}

func TestBackendForkResultUpdatesSessionID(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, cmd := m.Update(backendForkResultMsg{NewSessionID: "fork-xyz"})
	m = updated.(model)
	if m.sessionID != "fork-xyz" {
		t.Errorf("expected sessionID='fork-xyz', got '%s'", m.sessionID)
	}
	if cmd == nil {
		t.Error("expected Println cmd for fork confirmation")
	}
}

func TestBackendForkResultErrorSetsLastError(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, _ := m.Update(backendForkResultMsg{Error: "fork failed"})
	m = updated.(model)
	if m.lastError != "Fork failed: fork failed" {
		t.Errorf("expected fork error, got '%s'", m.lastError)
	}
}

// ========== Editor Done ==========

func TestEditorDoneSetsComposerContent(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80

	updated, _ := m.Update(editorDoneMsg{Content: "edited content from vim"})
	m = updated.(model)
	if m.composer.Value() != "edited content from vim" {
		t.Errorf("expected composer value from editor, got '%s'", m.composer.Value())
	}
}

func TestEditorDoneEmptyContentDoesNotClearComposer(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80
	m.composer.SetValue("existing text")

	updated, _ := m.Update(editorDoneMsg{Content: ""})
	m = updated.(model)
	if m.composer.Value() != "existing text" {
		t.Errorf("expected existing text preserved, got '%s'", m.composer.Value())
	}
}

// ========== Task State ==========

func TestBackendTaskStateUpdatesPanel(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.width = 80

	tasks := []taskEntry{
		{ID: "t1", Title: "Task 1", Status: "running"},
		{ID: "t2", Title: "Task 2", Status: "done"},
	}
	subagents := []subagentEntry{
		{ID: "s1", Type: "research", Status: "running", Summary: "searching"},
	}

	updated, _ := m.Update(backendTaskStateMsg{Tasks: tasks, Subagents: subagents})
	m = updated.(model)
	if len(m.taskPanelTasks) != 2 {
		t.Errorf("expected 2 tasks, got %d", len(m.taskPanelTasks))
	}
	if len(m.taskPanelSubagents) != 1 {
		t.Errorf("expected 1 subagent, got %d", len(m.taskPanelSubagents))
	}
}

// ========== Theme Detection ==========

func TestBgColorMsgSetsTheme(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, _ := m.Update(bgColorMsg{R: 30, G: 30, B: 30})
	m = updated.(model)
	if m.themeDetected != "dark" {
		t.Errorf("expected themeDetected='dark', got '%s'", m.themeDetected)
	}

	updated, _ = m.Update(bgColorMsg{R: 255, G: 255, B: 255})
	m = updated.(model)
	if m.themeDetected != "light" {
		t.Errorf("expected themeDetected='light', got '%s'", m.themeDetected)
	}
}

// ========== Queue Priority (Followup before Message) ==========

func TestFollowupDrainsBeforeMessageQueue(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.width = 80
	m.followupQueue = []string{"followup-first"}
	m.messageQueue = []string{"message-second"}

	// Token + tick to fill buffers
	m.tokenBuf.WriteString("response")
	updated, cmd := m.Update(backendDoneMsg{TokensIn: 10, TokensOut: 20})
	m = updated.(model)

	// Followup should be drained first — the returned batch should contain
	// a followupDrainMsg, not a queueDrainMsg
	if cmd == nil {
		t.Fatal("expected command batch from handleDone")
	}
	// The model should have moved to stageInput first, then followup drain
	// will send the message (which we simulate below)
	if len(m.followupQueue) != 1 {
		t.Errorf("expected 1 followup still queued (drain is async), got %d", len(m.followupQueue))
	}

	// Simulate followup drain
	updated, _ = m.Update(followupDrainMsg{})
	m = updated.(model)
	if m.stage != stageStreaming {
		t.Errorf("expected stageStreaming after followup drain, got %d", m.stage)
	}
	if len(m.followupQueue) != 0 {
		t.Errorf("expected followup queue empty after drain, got %d", len(m.followupQueue))
	}
}

func TestFollowupDrainEmptyIsNoop(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, _ := m.Update(followupDrainMsg{})
	m = updated.(model)
	if m.stage != stageInput {
		t.Errorf("expected stageInput unchanged on empty followup, got %d", m.stage)
	}
}

func TestQueueDrainEmptyIsNoop(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, _ := m.Update(queueDrainMsg{})
	m = updated.(model)
	if m.stage != stageInput {
		t.Errorf("expected stageInput unchanged on empty queue, got %d", m.stage)
	}
}

// ========== Resize During Overlays ==========

func TestResizeDuringApproval(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageApproval
	m.approvalOptions = []string{"Yes", "No"}
	m.approvalTool = "run_command"

	updated, cmd := m.Update(tea.WindowSizeMsg{Width: 200, Height: 50})
	m = updated.(model)
	if m.width != 200 {
		t.Errorf("expected width=200, got %d", m.width)
	}
	if m.stage != stageApproval {
		t.Errorf("expected stageApproval unchanged, got %d", m.stage)
	}
	if cmd == nil {
		t.Error("expected tickCmd for immediate re-render")
	}
}

func TestResizeDuringAskUser(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageAskUser
	m.askOptions = []string{"Option A", "Option B"}

	updated, cmd := m.Update(tea.WindowSizeMsg{Width: 160, Height: 45})
	m = updated.(model)
	if m.width != 160 {
		t.Errorf("expected width=160, got %d", m.width)
	}
	if cmd == nil {
		t.Error("expected tickCmd for immediate re-render")
	}
}

func TestResizeDuringModelPicker(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageModelPicker
	m.modelPickerEntries = []string{"a", "b", "c"}

	updated, cmd := m.Update(tea.WindowSizeMsg{Width: 100, Height: 30})
	m = updated.(model)
	if m.width != 100 {
		t.Errorf("expected width=100, got %d", m.width)
	}
	if cmd == nil {
		t.Error("expected tickCmd for immediate re-render")
	}
}

func TestResizeDuringSteer(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageSteer
	m.steerInput = "steer message"

	updated, cmd := m.Update(tea.WindowSizeMsg{Width: 140, Height: 35})
	m = updated.(model)
	if m.width != 140 {
		t.Errorf("expected width=140, got %d", m.width)
	}
	if cmd == nil {
		t.Error("expected tickCmd for immediate re-render")
	}
}

func TestResizeDuringPalette(t *testing.T) {
	m := initialModel(nil)
	m.stage = stagePalette

	updated, cmd := m.Update(tea.WindowSizeMsg{Width: 180, Height: 55})
	m = updated.(model)
	if m.width != 180 {
		t.Errorf("expected width=180, got %d", m.width)
	}
	if cmd == nil {
		t.Error("expected tickCmd for immediate re-render")
	}
}

// ========== Rapid Key Sequences ==========

func TestRapidDoubleEnterInInput(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80

	// First Enter sends chat
	m.composer.SetValue("hello")
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	m = updated.(model)
	if m.stage != stageStreaming {
		t.Fatalf("expected stageStreaming after first enter, got %d", m.stage)
	}

	// Second Enter queues (stageStreaming)
	m.composer.SetValue("world")
	updated, _ = m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	m = updated.(model)
	if len(m.messageQueue) != 1 {
		t.Errorf("expected 1 queued message after double enter, got %d", len(m.messageQueue))
	}
	if m.messageQueue[0] != "world" {
		t.Errorf("expected 'world' in queue, got '%s'", m.messageQueue[0])
	}
}

func TestEscapeThenEnterDuringStreaming(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.width = 80
	m.messageQueue = []string{"existing"}

	// Escape cancels and clears queue
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEscape}))
	m = updated.(model)
	if m.messageQueue != nil {
		t.Errorf("expected queue cleared after escape, got %v", m.messageQueue)
	}

	// Enter now tries to queue but composer may be empty
	m.composer.SetValue("")
	updated, _ = m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	m = updated.(model)
	// Empty composer should not queue
	if len(m.messageQueue) != 0 {
		t.Errorf("expected no queue from empty composer, got %d", len(m.messageQueue))
	}
}

func TestCtrlCInInputThenEnterClearsInterruptCount(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80

	// First Ctrl+C
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: 'c', Mod: tea.ModCtrl}))
	m = updated.(model)
	if m.interruptCount != 1 {
		t.Errorf("expected interruptCount=1, got %d", m.interruptCount)
	}

	// Type and send a message — should reset interruptCount
	m.composer.SetValue("hello")
	updated, _ = m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	m = updated.(model)
	if m.interruptCount != 0 {
		t.Errorf("expected interruptCount reset to 0 after send, got %d", m.interruptCount)
	}
	if m.stage != stageStreaming {
		t.Errorf("expected stageStreaming, got %d", m.stage)
	}
}

func TestCtrlKThenEscapeRestoresInputState(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80
	m.composer.SetValue("existing text")

	// Open palette
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: 'k', Mod: tea.ModCtrl}))
	m = updated.(model)
	if m.stage != stagePalette {
		t.Fatalf("expected stagePalette, got %d", m.stage)
	}

	// Close with Escape
	updated, _ = m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEscape}))
	m = updated.(model)
	if m.stage != stageInput {
		t.Errorf("expected stageInput, got %d", m.stage)
	}
	if !m.composer.Focused() {
		t.Error("expected composer focused after palette close")
	}
}

// ========== Streaming Under Long Tool Output ==========

func TestMultipleConcurrentToolCalls(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.width = 80

	// Three different tools running concurrently
	updated, _ := m.Update(backendToolCallMsg{Name: "read_file", Status: "running", Args: "/tmp/a"})
	m = updated.(model)
	updated, _ = m.Update(backendToolCallMsg{Name: "search_text", Status: "running", Args: "pattern"})
	m = updated.(model)
	updated, _ = m.Update(backendToolCallMsg{Name: "list_files", Status: "running", Args: "."})
	m = updated.(model)

	if len(m.toolCalls) != 3 {
		t.Fatalf("expected 3 tool calls, got %d", len(m.toolCalls))
	}

	// Complete them in different order
	updated, _ = m.Update(backendToolCallMsg{Name: "search_text", Status: "completed", Result: "found 5"})
	m = updated.(model)
	if m.toolCalls[1].Status != "completed" {
		t.Errorf("expected search_text completed, got %s", m.toolCalls[1].Status)
	}

	// View should show all three
	view := m.View().Content
	if !strings.Contains(view, "read_file") {
		t.Error("expected read_file in view")
	}
	if !strings.Contains(view, "search_text") {
		t.Error("expected search_text in view")
	}
	if !strings.Contains(view, "list_files") {
		t.Error("expected list_files in view")
	}
}

func TestToolCallErrorResultInView(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.width = 80

	updated, _ := m.Update(backendToolCallMsg{Name: "write_file", Status: "error", Result: "permission denied"})
	m = updated.(model)

	view := m.View().Content
	if !strings.Contains(view, "write_file") {
		t.Error("expected write_file in view")
	}
	if !strings.Contains(view, "permission denied") {
		t.Error("expected error result in view")
	}
}

// ========== Status Updates Don't Open Pickers ==========

func TestStatusUpdateDoesNotOpenAnyPicker(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80

	updated, _ := m.Update(backendStatusMsg{Model: "gpt-4", Provider: "openrouter", Mode: "auto"})
	m = updated.(model)
	if m.stage != stageInput {
		t.Errorf("status update should not change stage from input, got %d", m.stage)
	}
	if m.stage == stageModelPicker || m.stage == stageProviderPicker {
		t.Error("status update should not open pickers")
	}
}

func TestDoneDoesNotOpenPickers(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.width = 80
	m.tokenBuf.WriteString("response")

	updated, _ := m.Update(backendDoneMsg{TokensIn: 10, TokensOut: 20})
	m = updated.(model)
	if m.stage != stageInput {
		t.Errorf("expected stageInput after done, got %d", m.stage)
	}
	if m.stage == stageModelPicker || m.stage == stageProviderPicker {
		t.Error("done should not open pickers")
	}
}

// ========== Queue Debug Text Does Not Leak ==========

func TestQueueCountOnlyInStatusBar(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.width = 80
	m.messageQueue = []string{"msg1", "msg2", "msg3"}

	view := m.View().Content
	// The queue count should only appear in the status bar area
	// and not as a standalone debug line in the main view
	if strings.Contains(view, "(3 pending)") {
		t.Error("queue debug text should not leak into main view")
	}
}

// ========== Multiple Rapid Resizes ==========

func TestRapidResizeSequence(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	sizes := []struct{ w, h int }{
		{80, 24}, {120, 40}, {60, 20}, {200, 60}, {100, 30},
	}
	for _, sz := range sizes {
		updated, _ := m.Update(tea.WindowSizeMsg{Width: sz.w, Height: sz.h})
		m = updated.(model)
		if m.width != sz.w {
			t.Errorf("expected width=%d, got %d", sz.w, m.width)
		}
		if m.height != sz.h {
			t.Errorf("expected height=%d, got %d", sz.h, m.height)
		}
	}
}

// ========== Steer During Streaming ==========

func TestSteerCtrlCDoesNotCancel(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.width = 80
	b := NewBackend()
	m.backend = b

	// First Ctrl+C enters steer
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: 'c', Mod: tea.ModCtrl}))
	m = updated.(model)
	if m.stage != stageSteer {
		t.Fatalf("expected stageSteer, got %d", m.stage)
	}

	// Escape returns to streaming (not cancel)
	updated, _ = m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEscape}))
	m = updated.(model)
	if m.stage != stageStreaming {
		t.Errorf("expected stageStreaming after steer Escape, got %d", m.stage)
	}

	// Verify no cancel was sent
	select {
	case data := <-b.writeCh:
		s := string(data)
		if strings.Contains(s, "cancel") {
			t.Error("steer Escape should not send cancel")
		}
	default:
		// Good — no cancel sent
	}
}

func TestSteerEmptyMessageReturnsToStreaming(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageSteer
	m.steerInput = ""

	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
	m = updated.(model)
	if m.stage != stageStreaming {
		t.Errorf("expected stageStreaming after empty steer, got %d", m.stage)
	}
}

func TestSteerCtrlCSendsCancel(t *testing.T) {
	b := NewBackend()
	m := initialModel(nil)
	m.stage = stageSteer
	m.backend = b
	m.interruptCount = 1 // first Ctrl+C already counted

	// Ctrl+C in steer: since interruptCount >= 2 after increment, should quit
	updated, cmd := m.Update(tea.KeyPressMsg(tea.Key{Code: 'c', Mod: tea.ModCtrl}))
	m = updated.(model)
	if !m.quitting {
		t.Error("expected quitting after second Ctrl+C in steer")
	}
	_ = cmd
}

// ========== View rendering under quitting ==========

func TestViewEmptyWhenQuitting(t *testing.T) {
	m := initialModel(nil)
	m.quitting = true

	v := m.View()
	if v.Content != "" {
		t.Errorf("expected empty view when quitting, got '%s'", v.Content)
	}
}

// ========== Streaming token during wrong stage ==========

func TestTokenDuringInputStageDoesNotCrash(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80

	updated, cmd := m.Update(backendTokenMsg{Text: "hello"})
	m = updated.(model)
	if m.stage != stageInput {
		t.Errorf("token during input should not change stage, got %d", m.stage)
	}
	// Should return tea.Printf for direct printing
	if cmd == nil {
		t.Error("expected Printf cmd for token during input")
	}
}

func TestTokenEmptyTextDuringInputIsNoop(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	updated, cmd := m.Update(backendTokenMsg{Text: ""})
	m = updated.(model)
	if cmd != nil {
		t.Error("expected nil cmd for empty token during input")
	}
}

// ========== Plan Mode Rendering ==========

func TestPlanModeIndicatorInView(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80
	m.planMode = true

	view := m.View().Content
	if !strings.Contains(view, "PLAN MODE") {
		t.Errorf("expected PLAN MODE indicator in view")
	}
}

func TestPlanModeOffNotInView(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80
	m.planMode = false

	view := m.View().Content
	if strings.Contains(view, "PLAN MODE") {
		t.Error("PLAN MODE should not appear when planMode=false")
	}
}

// ========== Verify tickCmd used correctly ==========

func TestTickCmdReturnsNonNil(t *testing.T) {
	cmd := tickCmd()
	if cmd == nil {
		t.Error("tickCmd() should return non-nil")
	}
}

func TestStartupTimeoutCmdReturnsNonNil(t *testing.T) {
	cmd := startupTimeoutCmd()
	if cmd == nil {
		t.Error("startupTimeoutCmd() should return non-nil")
	}
}

// ========== Ensure done with cancelled flag works ==========

func TestDoneWithCancelledDoesNotCrash(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.width = 80
	m.tokenBuf.WriteString("partial")

	updated, _ := m.Update(backendDoneMsg{TokensIn: 5, TokensOut: 10, Cancelled: true})
	m = updated.(model)
	if m.stage != stageInput {
		t.Errorf("expected stageInput after cancelled done, got %d", m.stage)
	}
}

// ========== Composer focus after various flows ==========

func TestComposerFocusAfterWarningDuringStreaming(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.width = 80

	// Warning arrives during streaming
	updated, _ := m.Update(backendWarningMsg{Message: "low rate limit"})
	m = updated.(model)

	// Still streaming
	if m.stage != stageStreaming {
		t.Errorf("warning should not change stage, got %d", m.stage)
	}

	// Done arrives
	m.tokenBuf.WriteString("done")
	updated, _ = m.Update(backendDoneMsg{TokensIn: 10, TokensOut: 20})
	m = updated.(model)
	if m.stage != stageInput {
		t.Errorf("expected stageInput after done, got %d", m.stage)
	}
	if !m.composer.Focused() {
		t.Error("expected composer focused after done")
	}
}

// ========== Ensure tick during streaming flushes correctly ==========

func TestTickFlushesMultipleAccumulatedTokens(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.width = 80

	// Accumulate tokens without ticking — chain updates
	updated, _ := m.Update(backendTokenMsg{Text: "Hello "})
	m = updated.(model)
	updated, _ = m.Update(backendTokenMsg{Text: "World "})
	m = updated.(model)
	updated, _ = m.Update(backendTokenMsg{Text: "from "})
	m = updated.(model)
	updated, _ = m.Update(backendTokenMsg{Text: "AutoCode"})
	m = updated.(model)

	updated, _ = m.Update(tickMsg{Time: time.Now()})
	m = updated.(model)

	expected := "Hello World from AutoCode"
	if m.streamBuf.String() != expected {
		t.Errorf("expected streamBuf='%s', got '%s'", expected, m.streamBuf.String())
	}
	if m.tokenBuf.Len() != 0 {
		t.Error("expected tokenBuf empty after tick flush")
	}
}
