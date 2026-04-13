package main

import (
	"strings"
	"testing"
)

func TestViewShowsSpinnerWhileWaiting(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	// Empty buffers — should show spinner with a rotating verb
	view := m.View()
	if !strings.Contains(view, "…") {
		t.Errorf("expected spinner verb with '…' in view during empty streaming, got:\n%s", view)
	}
}

func TestViewShowsStreamingContent(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.streamBuf.WriteString("Hello from the model")

	view := m.View()
	if !strings.Contains(view, "Hello from the model") {
		t.Errorf("expected streaming content in view, got:\n%s", view)
	}
}

func TestViewShowsThinkingTokens(t *testing.T) {
	m := initialModel(nil)
	m.showThinking = true
	m.thinkingBuf.WriteString("I am reasoning about this")

	view := m.View()
	if !strings.Contains(view, "I am reasoning about this") {
		t.Errorf("expected thinking tokens in view when showThinking=true, got:\n%s", view)
	}
}

func TestViewHidesThinkingByDefault(t *testing.T) {
	m := initialModel(nil)
	m.showThinking = false
	m.thinkingBuf.WriteString("hidden reasoning")

	view := m.View()
	if strings.Contains(view, "hidden reasoning") {
		t.Errorf("expected thinking tokens hidden when showThinking=false, got:\n%s", view)
	}
}

func TestViewShowsToolCalls(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.toolCalls = []toolCallEntry{
		{Name: "read_file", Status: "running"},
	}

	view := m.View()
	if !strings.Contains(view, "read_file") {
		t.Errorf("expected tool call name in view, got:\n%s", view)
	}
}

func TestViewShowsToolCallError(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.toolCalls = []toolCallEntry{
		{Name: "write_file", Status: "error", Result: "permission denied"},
	}

	view := m.View()
	if !strings.Contains(view, "permission denied") {
		t.Errorf("expected error result in view, got:\n%s", view)
	}
}

func TestViewShowsToolCallResult(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.toolCalls = []toolCallEntry{
		{Name: "read_file", Status: "completed", Result: "file contents here"},
	}

	view := m.View()
	if !strings.Contains(view, "file contents here") {
		t.Errorf("expected tool result in view, got:\n%s", view)
	}
}

func TestViewShowsErrorMessage(t *testing.T) {
	m := initialModel(nil)
	m.lastError = "something went wrong"

	view := m.View()
	if !strings.Contains(view, "something went wrong") {
		t.Errorf("expected error message in view, got:\n%s", view)
	}
}

func TestViewShowsSeparator(t *testing.T) {
	m := initialModel(nil)
	m.width = 80

	view := m.View()
	if !strings.Contains(view, "─") {
		t.Errorf("expected separator line in view, got:\n%s", view)
	}
}

func TestViewShowsInputDuringStreaming(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.streamBuf.WriteString("streaming content")

	view := m.View()
	// composer.View() produces output containing the placeholder or cursor
	// Since composer is focused, it should show something
	if view == "" {
		t.Error("expected non-empty view during streaming")
	}
	// The default stage renders composer.View() which includes the placeholder
	// During streaming, the input is still shown (stage != approval/askUser)
}

func TestViewShowsApprovalPrompt(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageApproval
	m.approvalTool = "write_file"
	m.approvalArgs = `{"path": "/tmp/test.txt"}`
	m.approvalCursor = 0

	view := m.View()
	// Compact approval: title-cased tool name
	if !strings.Contains(view, "Write File") {
		t.Errorf("expected title-cased approval tool in view, got:\n%s", view)
	}
	if !strings.Contains(view, "Yes") {
		t.Errorf("expected approval options in view, got:\n%s", view)
	}
	if !strings.Contains(view, "●") {
		t.Errorf("expected ● prefix in approval view, got:\n%s", view)
	}
}

func TestViewShowsAskUserPrompt(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageAskUser
	m.askQuestion = "Which option?"
	m.askOptions = []string{"A", "B", "C"}
	m.askCursor = 0

	view := m.View()
	if !strings.Contains(view, "Which option?") {
		t.Errorf("expected ask-user question in view, got:\n%s", view)
	}
}

func TestViewShowsStatusBar(t *testing.T) {
	m := initialModel(nil)
	m.statusBar.Model = "qwen3:8b"

	view := m.View()
	if !strings.Contains(view, "qwen3:8b") {
		t.Errorf("expected model name in status bar, got:\n%s", view)
	}
}

func TestViewEmptyOnQuitting(t *testing.T) {
	m := initialModel(nil)
	m.quitting = true

	view := m.View()
	if view != "" {
		t.Errorf("expected empty view when quitting, got:\n%s", view)
	}
}

func TestViewToolCallResultTruncation(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	longResult := strings.Repeat("x", 200)
	m.toolCalls = []toolCallEntry{
		{Name: "read_file", Status: "completed", Result: longResult},
	}

	view := m.View()
	if strings.Contains(view, longResult) {
		t.Error("expected long result to be truncated in view")
	}
	if !strings.Contains(view, "...") {
		t.Error("expected truncation indicator '...' in view")
	}
}

func TestViewThinkingCappedAt5Lines(t *testing.T) {
	m := initialModel(nil)
	m.showThinking = true
	lines := make([]string, 10)
	for i := range lines {
		lines[i] = "thinking line"
	}
	m.thinkingBuf.WriteString(strings.Join(lines, "\n"))

	view := m.View()
	// Should show at most 5 lines of thinking
	// The first lines should be omitted
	thinkingCount := strings.Count(view, "thinking line")
	if thinkingCount > 5 {
		t.Errorf("expected at most 5 thinking lines in view, got %d", thinkingCount)
	}
}

func TestViewDuringStageInit(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInit
	m.width = 80

	view := m.View()

	// During init stage, should still render the composer and status bar
	// The default case in the switch renders composer
	if view == "" {
		t.Error("expected non-empty view during stageInit")
	}
	// Should contain status bar info (mode is always shown)
	if !strings.Contains(view, "suggest") {
		t.Errorf("expected mode in init view status bar, got:\n%s", view)
	}
	// Should contain separator
	if !strings.Contains(view, "─") {
		t.Errorf("expected separator in init view, got:\n%s", view)
	}
}

func TestViewStreamBufCappedAt50Lines(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	lines := make([]string, 60)
	for i := range lines {
		lines[i] = "content line"
	}
	m.streamBuf.WriteString(strings.Join(lines, "\n"))

	view := m.View()
	if !strings.Contains(view, "lines above") {
		t.Error("expected '[N lines above]' indicator for long streaming content")
	}
}

func TestViewTaskPanelHiddenInInput(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.taskPanelTasks = []taskEntry{
		{Title: "hidden-task", Status: "in_progress"},
	}

	view := m.View()
	if strings.Contains(view, "hidden-task") {
		t.Error("expected task panel to be hidden during input stage (chat-first)")
	}
}

func TestViewTaskPanelVisibleDuringStreaming(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.streamBuf.WriteString("some output")
	m.taskPanelTasks = []taskEntry{
		{Title: "active-task", Status: "in_progress"},
	}

	view := m.View()
	if !strings.Contains(view, "active-task") {
		t.Errorf("expected task panel to be visible during streaming, got:\n%s", view)
	}
}

func TestViewNarrowTerminalToolTruncation(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.width = 40
	longResult := strings.Repeat("x", 200)
	m.toolCalls = []toolCallEntry{
		{Name: "read_file", Status: "completed", Result: longResult},
	}

	view := m.View()
	if strings.Contains(view, longResult) {
		t.Error("expected tool result to be truncated at narrow width")
	}
	if !strings.Contains(view, "...") {
		t.Error("expected truncation indicator in narrow terminal")
	}
}

func TestViewToolCallUsesElbow(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming
	m.toolCalls = []toolCallEntry{
		{Name: "bash", Status: "running"},
	}

	view := m.View()
	if !strings.Contains(view, "⎿") {
		t.Errorf("expected ⎿ prefix for tool calls, got:\n%s", view)
	}
}
