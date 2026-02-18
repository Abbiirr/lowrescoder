package main

import (
	"testing"
)

func TestInitialModelDefaults(t *testing.T) {
	m := initialModel(nil)

	if m.stage != stageInit {
		t.Errorf("expected stageInit, got %d", m.stage)
	}
	if m.quitting {
		t.Error("expected quitting=false")
	}
	if !m.showThinking {
		t.Error("expected showThinking=true by default")
	}
	if m.queueMax != 10 {
		t.Errorf("expected queueMax=10, got %d", m.queueMax)
	}
	if m.interruptCount != 0 {
		t.Errorf("expected interruptCount=0, got %d", m.interruptCount)
	}
	if len(m.approvalOptions) != 3 {
		t.Errorf("expected 3 approval options, got %d", len(m.approvalOptions))
	}
	if m.statusBar.Model != "..." {
		t.Errorf("expected statusBar.Model=..., got %s", m.statusBar.Model)
	}
	if m.statusBar.Provider != "..." {
		t.Errorf("expected statusBar.Provider=..., got %s", m.statusBar.Provider)
	}
	if m.statusBar.Mode != "suggest" {
		t.Errorf("expected statusBar.Mode=suggest, got %s", m.statusBar.Mode)
	}
}

func TestInitialModelTextInput(t *testing.T) {
	m := initialModel(nil)

	if m.textInput.CharLimit != 2000 {
		t.Errorf("expected charLimit=2000, got %d", m.textInput.CharLimit)
	}
	if m.textInput.Placeholder != "Type a message..." {
		t.Errorf("expected placeholder='Type a message...', got '%s'", m.textInput.Placeholder)
	}
}

func TestInitialModelBackendRef(t *testing.T) {
	backend := NewBackend()
	m := initialModel(backend)

	if m.backend != backend {
		t.Error("expected backend reference to match")
	}
}

func TestInitialModelInit(t *testing.T) {
	m := initialModel(nil)
	cmd := m.Init()
	if cmd == nil {
		t.Error("expected Init to return a command")
	}
}

func TestTickCmd(t *testing.T) {
	cmd := tickCmd()
	if cmd == nil {
		t.Error("expected tickCmd to return a command")
	}
}

func TestStageConstants(t *testing.T) {
	// Verify stages are distinct
	stages := []stage{stageInit, stageInput, stageStreaming, stageApproval, stageAskUser}
	seen := make(map[stage]bool)
	for _, s := range stages {
		if seen[s] {
			t.Errorf("duplicate stage value: %d", s)
		}
		seen[s] = true
	}
}
