package main

import (
	"testing"

	tea "github.com/charmbracelet/bubbletea"
)

func TestEnterApproval(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageStreaming

	result := enterApproval(m, backendApprovalRequestMsg{
		RequestID: 42,
		Tool:      "write_file",
		Args:      `{"path": "/tmp/test.txt"}`,
	})

	if result.stage != stageApproval {
		t.Errorf("expected stageApproval, got %d", result.stage)
	}
	if result.approvalRequestID != 42 {
		t.Errorf("expected requestID=42, got %d", result.approvalRequestID)
	}
	if result.approvalTool != "write_file" {
		t.Errorf("expected tool=write_file, got %s", result.approvalTool)
	}
	if result.approvalCursor != 0 {
		t.Errorf("expected cursor=0, got %d", result.approvalCursor)
	}
}

func TestApprovalKeyUp(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageApproval
	m.approvalCursor = 0

	// Up should wrap to last option
	updated, _ := handleApprovalKey(m, tea.KeyMsg{Type: tea.KeyUp})
	um := updated.(model)

	if um.approvalCursor != 2 {
		t.Errorf("expected cursor=2 (wrap), got %d", um.approvalCursor)
	}
}

func TestApprovalKeyDown(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageApproval
	m.approvalCursor = 2

	// Down should wrap to first option
	updated, _ := handleApprovalKey(m, tea.KeyMsg{Type: tea.KeyDown})
	um := updated.(model)

	if um.approvalCursor != 0 {
		t.Errorf("expected cursor=0 (wrap), got %d", um.approvalCursor)
	}
}

func TestApprovalKeyDownNormal(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageApproval
	m.approvalCursor = 0

	updated, _ := handleApprovalKey(m, tea.KeyMsg{Type: tea.KeyDown})
	um := updated.(model)

	if um.approvalCursor != 1 {
		t.Errorf("expected cursor=1, got %d", um.approvalCursor)
	}
}

func TestApprovalKeyUpNormal(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageApproval
	m.approvalCursor = 2

	updated, _ := handleApprovalKey(m, tea.KeyMsg{Type: tea.KeyUp})
	um := updated.(model)

	if um.approvalCursor != 1 {
		t.Errorf("expected cursor=1, got %d", um.approvalCursor)
	}
}

func TestApprovalEnterYes(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageApproval
	m.approvalCursor = 0 // "Yes"

	updated, _ := handleApprovalKey(m, tea.KeyMsg{Type: tea.KeyEnter})
	um := updated.(model)

	if um.stage != stageStreaming {
		t.Errorf("expected stageStreaming after approval, got %d", um.stage)
	}
}

func TestApprovalEnterNo(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageApproval
	m.approvalCursor = 2 // "No"

	updated, _ := handleApprovalKey(m, tea.KeyMsg{Type: tea.KeyEnter})
	um := updated.(model)

	if um.stage != stageStreaming {
		t.Errorf("expected stageStreaming after denial, got %d", um.stage)
	}
}

func TestApprovalEnterSessionApprove(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageApproval
	m.approvalCursor = 1 // "Yes, this session"

	updated, _ := handleApprovalKey(m, tea.KeyMsg{Type: tea.KeyEnter})
	um := updated.(model)

	if um.stage != stageStreaming {
		t.Errorf("expected stageStreaming, got %d", um.stage)
	}
}

func TestApprovalEscape(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageApproval

	updated, _ := handleApprovalKey(m, tea.KeyMsg{Type: tea.KeyEscape})
	um := updated.(model)

	if um.stage != stageStreaming {
		t.Errorf("expected stageStreaming after escape, got %d", um.stage)
	}
}

func TestApprovalCtrlC(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageApproval

	updated, _ := handleApprovalKey(m, tea.KeyMsg{Type: tea.KeyCtrlC})
	um := updated.(model)

	if um.stage != stageStreaming {
		t.Errorf("expected stageStreaming after Ctrl+C, got %d", um.stage)
	}
}

func TestRenderApprovalView(t *testing.T) {
	m := initialModel(nil)
	m.approvalTool = "write_file"
	m.approvalArgs = `{"path": "/tmp/test.txt"}`
	m.approvalCursor = 0

	view := renderApprovalView(m)

	if view == "" {
		t.Error("expected non-empty approval view")
	}
	// Should contain the tool name
	if !containsString(view, "write_file") {
		t.Error("expected view to contain tool name")
	}
}

func TestRenderApprovalViewLongArgs(t *testing.T) {
	m := initialModel(nil)
	m.approvalTool = "write_file"
	// Long args that should be truncated
	lines := ""
	for i := 0; i < 10; i++ {
		lines += "line " + string(rune('0'+i)) + "\n"
	}
	m.approvalArgs = lines
	m.approvalCursor = 1

	view := renderApprovalView(m)

	if view == "" {
		t.Error("expected non-empty view even with long args")
	}
}

func containsString(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > 0 && findSubstring(s, substr))
}

func findSubstring(s, sub string) bool {
	for i := 0; i <= len(s)-len(sub); i++ {
		if s[i:i+len(sub)] == sub {
			return true
		}
	}
	return false
}
