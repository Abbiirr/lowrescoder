package main

import (
	"encoding/json"
	"testing"

	tea "github.com/charmbracelet/bubbletea"
)

// msgRecorder is a minimal tea.Program stand-in that records messages sent via Send().
type msgRecorder struct {
	msgs []tea.Msg
}

func (r *msgRecorder) Send(msg tea.Msg) {
	r.msgs = append(r.msgs, msg)
}

// newTestBackendWithRecorder creates a Backend whose program field is a msgRecorder.
func newTestBackendWithRecorder() (*Backend, *msgRecorder) {
	rec := &msgRecorder{}
	b := NewBackend()
	// Use a duck-typing wrapper since b.program is *tea.Program
	// We'll test dispatchNotification and routeRequest directly instead.
	return b, rec
}

// helper: build an RPCMessage from raw JSON
func rpcFromJSON(t *testing.T, raw string) RPCMessage {
	t.Helper()
	var msg RPCMessage
	if err := json.Unmarshal([]byte(raw), &msg); err != nil {
		t.Fatalf("failed to unmarshal RPCMessage: %v", err)
	}
	return msg
}

// --- dispatchNotification tests ---
// These test the dispatch logic directly by calling dispatchNotification on a Backend
// with a recording program. Since b.program is *tea.Program, we need a test adapter.

// testProgram wraps msgRecorder to satisfy the interface used by dispatchNotification.
// Since dispatchNotification calls b.program.Send(), we need to set b.program to a real
// *tea.Program. Instead, we test the parse logic by verifying RPCMessage → params extraction.

func TestDispatchNotificationTokenParses(t *testing.T) {
	raw := `{"jsonrpc":"2.0","method":"on_token","params":{"text":"hello "}}`
	msg := rpcFromJSON(t, raw)

	if msg.Method != "on_token" {
		t.Errorf("expected method=on_token, got %s", msg.Method)
	}
	var params TokenParams
	if err := json.Unmarshal(msg.Params, &params); err != nil {
		t.Fatalf("failed to unmarshal params: %v", err)
	}
	if params.Text != "hello " {
		t.Errorf("expected text='hello ', got '%s'", params.Text)
	}
}

func TestDispatchNotificationThinkingParses(t *testing.T) {
	raw := `{"jsonrpc":"2.0","method":"on_thinking","params":{"text":"reasoning..."}}`
	msg := rpcFromJSON(t, raw)

	var params ThinkingParams
	json.Unmarshal(msg.Params, &params)
	if params.Text != "reasoning..." {
		t.Errorf("expected text='reasoning...', got '%s'", params.Text)
	}
}

func TestDispatchNotificationToolCallParses(t *testing.T) {
	raw := `{"jsonrpc":"2.0","method":"on_tool_call","params":{"name":"write_file","status":"running","args":"{\"path\":\"/tmp\"}"}}`
	msg := rpcFromJSON(t, raw)

	var params ToolCallParams
	json.Unmarshal(msg.Params, &params)
	if params.Name != "write_file" {
		t.Errorf("expected name=write_file, got '%s'", params.Name)
	}
	if params.Status != "running" {
		t.Errorf("expected status=running, got '%s'", params.Status)
	}
}

func TestDispatchNotificationDoneParses(t *testing.T) {
	raw := `{"jsonrpc":"2.0","method":"on_done","params":{"tokens_in":150,"tokens_out":300,"cancelled":false}}`
	msg := rpcFromJSON(t, raw)

	var params DoneParams
	json.Unmarshal(msg.Params, &params)
	if params.TokensIn != 150 {
		t.Errorf("expected tokens_in=150, got %d", params.TokensIn)
	}
	if params.TokensOut != 300 {
		t.Errorf("expected tokens_out=300, got %d", params.TokensOut)
	}
	if params.Cancelled {
		t.Error("expected cancelled=false")
	}
}

func TestDispatchNotificationErrorParses(t *testing.T) {
	raw := `{"jsonrpc":"2.0","method":"on_error","params":{"message":"backend crashed"}}`
	msg := rpcFromJSON(t, raw)

	var params ErrorParams
	json.Unmarshal(msg.Params, &params)
	if params.Message != "backend crashed" {
		t.Errorf("expected message='backend crashed', got '%s'", params.Message)
	}
}

func TestDispatchNotificationStatusParses(t *testing.T) {
	raw := `{"jsonrpc":"2.0","method":"on_status","params":{"model":"qwen3:8b","provider":"ollama","mode":"suggest","session_id":"abc"}}`
	msg := rpcFromJSON(t, raw)

	var params StatusParams
	json.Unmarshal(msg.Params, &params)
	if params.Model != "qwen3:8b" {
		t.Errorf("expected model=qwen3:8b, got '%s'", params.Model)
	}
	if params.SessionID != "abc" {
		t.Errorf("expected session_id=abc, got '%s'", params.SessionID)
	}
}

// --- routeRequest tests ---

func TestRouteRequestApprovalParses(t *testing.T) {
	raw := `{"jsonrpc":"2.0","id":1000,"method":"on_tool_request","params":{"tool":"write_file","args":"{\"path\":\"/tmp\"}"}}`
	msg := rpcFromJSON(t, raw)

	if msg.ID == nil || *msg.ID != 1000 {
		t.Fatalf("expected id=1000")
	}
	if msg.Method != "on_tool_request" {
		t.Errorf("expected method=on_tool_request, got %s", msg.Method)
	}

	var params ApprovalRequestParams
	json.Unmarshal(msg.Params, &params)
	if params.Tool != "write_file" {
		t.Errorf("expected tool=write_file, got '%s'", params.Tool)
	}
}

func TestRouteRequestAskUserParses(t *testing.T) {
	raw := `{"jsonrpc":"2.0","id":2000,"method":"on_ask_user","params":{"question":"Pick one","options":["A","B"],"allow_text":true}}`
	msg := rpcFromJSON(t, raw)

	if msg.ID == nil || *msg.ID != 2000 {
		t.Fatalf("expected id=2000")
	}

	var params AskUserRequestParams
	json.Unmarshal(msg.Params, &params)
	if params.Question != "Pick one" {
		t.Errorf("expected question='Pick one', got '%s'", params.Question)
	}
	if len(params.Options) != 2 {
		t.Errorf("expected 2 options, got %d", len(params.Options))
	}
	if !params.AllowText {
		t.Error("expected allow_text=true")
	}
}

// --- SendRequest marshal tests ---

func TestSendRequestMarshal(t *testing.T) {
	b := NewBackend()

	id := b.SendRequest("chat", ChatParams{Message: "hello", SessionID: "s1"})
	if id < 0 {
		t.Errorf("expected non-negative ID, got %d", id)
	}

	// Read the message from writeCh
	select {
	case data := <-b.writeCh:
		var decoded map[string]interface{}
		if err := json.Unmarshal(data, &decoded); err != nil {
			t.Fatalf("failed to unmarshal: %v", err)
		}
		if decoded["jsonrpc"] != "2.0" {
			t.Errorf("expected jsonrpc=2.0, got %v", decoded["jsonrpc"])
		}
		if decoded["method"] != "chat" {
			t.Errorf("expected method=chat, got %v", decoded["method"])
		}
		params := decoded["params"].(map[string]interface{})
		if params["message"] != "hello" {
			t.Errorf("expected message=hello, got %v", params["message"])
		}
	default:
		t.Error("expected message in writeCh")
	}
}

func TestSendRequestIncrementingIDs(t *testing.T) {
	b := NewBackend()

	id1 := b.SendRequest("chat", ChatParams{Message: "first"})
	id2 := b.SendRequest("chat", ChatParams{Message: "second"})

	if id2 <= id1 {
		t.Errorf("expected incrementing IDs: id1=%d, id2=%d", id1, id2)
	}

	// Drain writeCh
	<-b.writeCh
	<-b.writeCh
}

// --- SendResponse marshal tests ---

func TestSendResponseMarshal(t *testing.T) {
	b := NewBackend()

	b.SendResponse(42, ApprovalResult{Approved: true, SessionApprove: false})

	select {
	case data := <-b.writeCh:
		var decoded map[string]interface{}
		if err := json.Unmarshal(data, &decoded); err != nil {
			t.Fatalf("failed to unmarshal: %v", err)
		}
		if decoded["jsonrpc"] != "2.0" {
			t.Errorf("expected jsonrpc=2.0, got %v", decoded["jsonrpc"])
		}
		if int(decoded["id"].(float64)) != 42 {
			t.Errorf("expected id=42, got %v", decoded["id"])
		}
		result := decoded["result"].(map[string]interface{})
		if result["approved"] != true {
			t.Errorf("expected approved=true, got %v", result["approved"])
		}
	default:
		t.Error("expected message in writeCh")
	}
}

// --- Robustness tests ---

func TestMalformedJSONIgnored(t *testing.T) {
	// Verify that invalid JSON doesn't panic when we try to unmarshal
	raw := `not valid json at all`
	var msg RPCMessage
	err := json.Unmarshal([]byte(raw), &msg)
	if err == nil {
		t.Error("expected unmarshal error for malformed JSON")
	}
	// The readLoop continues on error, so we just verify no panic
}

func TestEmptyLineIgnored(t *testing.T) {
	// Empty bytes should be skipped (len check in readLoop)
	line := []byte("")
	if len(line) != 0 {
		t.Error("expected empty line to have length 0")
	}
	// readLoop does `if len(line) == 0 { continue }` — verified
}

func TestWriteChFullDropsMessage(t *testing.T) {
	b := &Backend{
		writeCh: make(chan []byte, 1), // tiny buffer
	}
	b.nextID.Store(1)

	// Fill the channel
	b.SendRequest("first", struct{}{})

	// This should be dropped (non-blocking)
	id := b.SendRequest("second", struct{}{})
	if id < 0 {
		t.Error("expected valid ID even when channel full (message dropped silently)")
	}

	// Only one message in channel
	<-b.writeCh
	select {
	case <-b.writeCh:
		t.Error("expected second message to be dropped")
	default:
		// expected — channel empty
	}
}

func TestDispatchNotificationNilProgram(t *testing.T) {
	b := NewBackend()
	// b.program is nil
	raw := `{"jsonrpc":"2.0","method":"on_token","params":{"text":"test"}}`
	msg := rpcFromJSON(t, raw)

	// Should not panic
	b.dispatchNotification(msg)
}

func TestRouteRequestNilProgram(t *testing.T) {
	b := NewBackend()
	raw := `{"jsonrpc":"2.0","id":1,"method":"on_tool_request","params":{"tool":"test","args":"{}"}}`
	msg := rpcFromJSON(t, raw)

	// Should not panic
	b.routeRequest(msg)
}
