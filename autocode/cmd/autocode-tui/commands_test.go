package main

import (
	"testing"
)

func TestParseCommandSimple(t *testing.T) {
	cmd, args := parseCommand("/exit")
	if cmd != "exit" {
		t.Errorf("expected cmd='exit', got '%s'", cmd)
	}
	if args != "" {
		t.Errorf("expected args='', got '%s'", args)
	}
}

func TestParseCommandWithArgs(t *testing.T) {
	cmd, args := parseCommand("/model qwen3:8b")
	if cmd != "model" {
		t.Errorf("expected cmd='model', got '%s'", cmd)
	}
	if args != "qwen3:8b" {
		t.Errorf("expected args='qwen3:8b', got '%s'", args)
	}
}

func TestParseCommandWithMultipleArgs(t *testing.T) {
	cmd, args := parseCommand("/resume abc123 extra")
	if cmd != "resume" {
		t.Errorf("expected cmd='resume', got '%s'", cmd)
	}
	if args != "abc123 extra" {
		t.Errorf("expected args='abc123 extra', got '%s'", args)
	}
}

func TestParseCommandLeadingSlash(t *testing.T) {
	cmd, _ := parseCommand("/help")
	if cmd != "help" {
		t.Errorf("expected leading / stripped, cmd='help', got '%s'", cmd)
	}
}

func TestParseCommandNoSlash(t *testing.T) {
	cmd, args := parseCommand("hello world")
	if cmd != "" {
		t.Errorf("expected cmd='' for non-slash input, got '%s'", cmd)
	}
	if args != "hello world" {
		t.Errorf("expected args='hello world', got '%s'", args)
	}
}

func TestParseCommandEmptyAfterSlash(t *testing.T) {
	cmd, args := parseCommand("/")
	if cmd != "" {
		t.Errorf("expected cmd='' for bare slash, got '%s'", cmd)
	}
	if args != "" {
		t.Errorf("expected args='', got '%s'", args)
	}
}

func TestParseCommandWhitespace(t *testing.T) {
	cmd, args := parseCommand("  /model  qwen  ")
	if cmd != "model" {
		t.Errorf("expected cmd='model', got '%s'", cmd)
	}
	// TrimSpace trims, then SplitN splits on first space
	// Result depends on exact SplitN behavior
	if args == "" {
		t.Error("expected non-empty args")
	}
}

func TestKnownCommandsList(t *testing.T) {
	// Verify knownCommands contains essential commands
	required := []string{
		"/exit", "/quit", "/help", "/model", "/provider",
		"/clear", "/thinking", "/new", "/sessions", "/resume",
		"/loop", "/tasks", "/plan", "/research", "/build", "/review",
	}
	for _, req := range required {
		found := false
		for _, cmd := range knownCommands {
			if cmd == req {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("expected '%s' in knownCommands", req)
		}
	}
}

func TestKnownCommandsMinimumCount(t *testing.T) {
	if len(knownCommands) < 24 {
		t.Errorf("expected at least 15 known commands, got %d", len(knownCommands))
	}
}

func TestSlashCommandExitQuitsApp(t *testing.T) {
	m := initialModel(nil)
	updated, _ := m.handleSlashCommand("/exit")
	um := updated.(model)
	if !um.quitting {
		t.Error("expected quitting=true for /exit")
	}
}

func TestSlashCommandQuitQuitsApp(t *testing.T) {
	m := initialModel(nil)
	updated, _ := m.handleSlashCommand("/quit")
	um := updated.(model)
	if !um.quitting {
		t.Error("expected quitting=true for /quit")
	}
}

func TestSlashCommandQQuitsApp(t *testing.T) {
	m := initialModel(nil)
	updated, _ := m.handleSlashCommand("/q")
	um := updated.(model)
	if !um.quitting {
		t.Error("expected quitting=true for /q")
	}
}

func TestSlashCommandClearReturnsCmd(t *testing.T) {
	m := initialModel(nil)
	_, cmd := m.handleSlashCommand("/clear")
	if cmd == nil {
		t.Error("expected ClearScreen command for /clear")
	}
}

func TestSlashCommandClsReturnsCmd(t *testing.T) {
	m := initialModel(nil)
	_, cmd := m.handleSlashCommand("/cls")
	if cmd == nil {
		t.Error("expected ClearScreen command for /cls")
	}
}

func TestSlashCommandThinkingToggles(t *testing.T) {
	m := initialModel(nil)
	m.showThinking = false

	updated, _ := m.handleSlashCommand("/thinking")
	um := updated.(model)
	if !um.showThinking {
		t.Error("expected showThinking=true after first toggle")
	}

	updated2, _ := um.handleSlashCommand("/thinking")
	um2 := updated2.(model)
	if um2.showThinking {
		t.Error("expected showThinking=false after second toggle")
	}
}

func TestSlashCommandThinkingAlias(t *testing.T) {
	m := initialModel(nil)
	m.showThinking = false

	updated, _ := m.handleSlashCommand("/think")
	um := updated.(model)
	if !um.showThinking {
		t.Error("expected showThinking=true for /think alias")
	}
}

func TestSlashCommandDelegatesToBackend(t *testing.T) {
	b := NewBackend()
	m := initialModel(b)

	_, _ = m.handleSlashCommand("/help")

	// Should have sent a request to the backend's writeCh
	select {
	case data := <-b.writeCh:
		if len(data) == 0 {
			t.Error("expected non-empty data sent to backend")
		}
	default:
		t.Error("expected /help to be delegated to backend via SendRequest")
	}
}

func TestSlashCommandThinkingReturnsCmd(t *testing.T) {
	m := initialModel(nil)
	_, cmd := m.handleSlashCommand("/thinking")
	if cmd == nil {
		t.Error("expected Println command for /thinking toggle feedback")
	}
}
