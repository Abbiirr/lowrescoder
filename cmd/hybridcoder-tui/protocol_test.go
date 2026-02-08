package main

import (
	"encoding/json"
	"testing"
)

// --- RPCRequest tests ---

func TestRPCRequestMarshal(t *testing.T) {
	req := RPCRequest{
		JSONRPC: "2.0",
		ID:      1,
		Method:  "chat",
		Params:  ChatParams{Message: "hello", SessionID: "abc"},
	}
	data, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("marshal error: %v", err)
	}

	var decoded map[string]interface{}
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}

	if decoded["jsonrpc"] != "2.0" {
		t.Errorf("expected jsonrpc=2.0, got %v", decoded["jsonrpc"])
	}
	if decoded["method"] != "chat" {
		t.Errorf("expected method=chat, got %v", decoded["method"])
	}
	if decoded["id"].(float64) != 1 {
		t.Errorf("expected id=1, got %v", decoded["id"])
	}

	params := decoded["params"].(map[string]interface{})
	if params["message"] != "hello" {
		t.Errorf("expected message=hello, got %v", params["message"])
	}
}

func TestRPCRequestMarshalCancel(t *testing.T) {
	req := RPCRequest{
		JSONRPC: "2.0",
		ID:      5,
		Method:  "cancel",
		Params:  CancelParams{},
	}
	data, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("marshal error: %v", err)
	}

	var decoded map[string]interface{}
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if decoded["method"] != "cancel" {
		t.Errorf("expected method=cancel, got %v", decoded["method"])
	}
}

func TestRPCRequestMarshalCommand(t *testing.T) {
	req := RPCRequest{
		JSONRPC: "2.0",
		ID:      3,
		Method:  "command",
		Params:  CommandParams{Cmd: "/help"},
	}
	data, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("marshal error: %v", err)
	}

	var decoded map[string]interface{}
	json.Unmarshal(data, &decoded)
	params := decoded["params"].(map[string]interface{})
	if params["cmd"] != "/help" {
		t.Errorf("expected cmd=/help, got %v", params["cmd"])
	}
}

func TestRPCRequestMarshalSessionNew(t *testing.T) {
	req := RPCRequest{
		JSONRPC: "2.0",
		ID:      10,
		Method:  "session.new",
		Params:  SessionNewParams{Title: "Test session"},
	}
	data, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("marshal error: %v", err)
	}

	var decoded map[string]interface{}
	json.Unmarshal(data, &decoded)
	params := decoded["params"].(map[string]interface{})
	if params["title"] != "Test session" {
		t.Errorf("expected title=Test session, got %v", params["title"])
	}
}

func TestRPCRequestMarshalConfigSet(t *testing.T) {
	req := RPCRequest{
		JSONRPC: "2.0",
		ID:      20,
		Method:  "config.set",
		Params:  ConfigSetParams{Key: "llm.model", Value: "qwen3:8b"},
	}
	data, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("marshal error: %v", err)
	}

	var decoded map[string]interface{}
	json.Unmarshal(data, &decoded)
	params := decoded["params"].(map[string]interface{})
	if params["key"] != "llm.model" {
		t.Errorf("expected key=llm.model, got %v", params["key"])
	}
	if params["value"] != "qwen3:8b" {
		t.Errorf("expected value=qwen3:8b, got %v", params["value"])
	}
}

// --- RPCResponse tests ---

func TestRPCResponseMarshal(t *testing.T) {
	resp := RPCResponse{
		JSONRPC: "2.0",
		ID:      1,
		Result:  ApprovalResult{Approved: true, SessionApprove: false},
	}
	data, err := json.Marshal(resp)
	if err != nil {
		t.Fatalf("marshal error: %v", err)
	}

	var decoded map[string]interface{}
	json.Unmarshal(data, &decoded)
	if decoded["jsonrpc"] != "2.0" {
		t.Errorf("expected jsonrpc=2.0, got %v", decoded["jsonrpc"])
	}
	result := decoded["result"].(map[string]interface{})
	if result["approved"] != true {
		t.Errorf("expected approved=true, got %v", result["approved"])
	}
}

func TestRPCResponseAskUser(t *testing.T) {
	resp := RPCResponse{
		JSONRPC: "2.0",
		ID:      1000,
		Result:  AskUserResult{Answer: "Option A"},
	}
	data, err := json.Marshal(resp)
	if err != nil {
		t.Fatalf("marshal error: %v", err)
	}

	var decoded map[string]interface{}
	json.Unmarshal(data, &decoded)
	result := decoded["result"].(map[string]interface{})
	if result["answer"] != "Option A" {
		t.Errorf("expected answer=Option A, got %v", result["answer"])
	}
}

// --- RPCMessage unmarshal tests ---

func TestRPCMessageUnmarshalNotification(t *testing.T) {
	raw := `{"jsonrpc":"2.0","method":"on_token","params":{"text":"hello "}}`
	var msg RPCMessage
	if err := json.Unmarshal([]byte(raw), &msg); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if msg.Method != "on_token" {
		t.Errorf("expected method=on_token, got %v", msg.Method)
	}
	if msg.ID != nil {
		t.Errorf("expected nil ID for notification, got %v", *msg.ID)
	}

	var params TokenParams
	if err := json.Unmarshal(msg.Params, &params); err != nil {
		t.Fatalf("params unmarshal error: %v", err)
	}
	if params.Text != "hello " {
		t.Errorf("expected text='hello ', got %v", params.Text)
	}
}

func TestRPCMessageUnmarshalRequest(t *testing.T) {
	raw := `{"jsonrpc":"2.0","id":1000,"method":"on_tool_request","params":{"tool":"write_file","args":"{\"path\":\"/tmp/test\"}"}}`
	var msg RPCMessage
	if err := json.Unmarshal([]byte(raw), &msg); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if msg.Method != "on_tool_request" {
		t.Errorf("expected method=on_tool_request, got %v", msg.Method)
	}
	if msg.ID == nil || *msg.ID != 1000 {
		t.Errorf("expected id=1000")
	}

	var params ApprovalRequestParams
	if err := json.Unmarshal(msg.Params, &params); err != nil {
		t.Fatalf("params unmarshal error: %v", err)
	}
	if params.Tool != "write_file" {
		t.Errorf("expected tool=write_file, got %v", params.Tool)
	}
}

func TestRPCMessageUnmarshalResponse(t *testing.T) {
	raw := `{"jsonrpc":"2.0","id":1,"result":{"ok":true}}`
	var msg RPCMessage
	if err := json.Unmarshal([]byte(raw), &msg); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if msg.Method != "" {
		t.Errorf("expected empty method for response, got %v", msg.Method)
	}
	if msg.ID == nil || *msg.ID != 1 {
		t.Errorf("expected id=1")
	}
}

func TestRPCMessageUnmarshalDoneNotification(t *testing.T) {
	raw := `{"jsonrpc":"2.0","method":"on_done","params":{"tokens_in":100,"tokens_out":200}}`
	var msg RPCMessage
	json.Unmarshal([]byte(raw), &msg)

	var params DoneParams
	json.Unmarshal(msg.Params, &params)
	if params.TokensIn != 100 {
		t.Errorf("expected tokens_in=100, got %d", params.TokensIn)
	}
	if params.TokensOut != 200 {
		t.Errorf("expected tokens_out=200, got %d", params.TokensOut)
	}
}

func TestRPCMessageUnmarshalThinking(t *testing.T) {
	raw := `{"jsonrpc":"2.0","method":"on_thinking","params":{"text":"reasoning..."}}`
	var msg RPCMessage
	json.Unmarshal([]byte(raw), &msg)

	var params ThinkingParams
	json.Unmarshal(msg.Params, &params)
	if params.Text != "reasoning..." {
		t.Errorf("expected text=reasoning..., got %v", params.Text)
	}
}

func TestRPCMessageUnmarshalToolCall(t *testing.T) {
	raw := `{"jsonrpc":"2.0","method":"on_tool_call","params":{"name":"read_file","status":"completed","result":"file contents here"}}`
	var msg RPCMessage
	json.Unmarshal([]byte(raw), &msg)

	var params ToolCallParams
	json.Unmarshal(msg.Params, &params)
	if params.Name != "read_file" {
		t.Errorf("expected name=read_file, got %v", params.Name)
	}
	if params.Status != "completed" {
		t.Errorf("expected status=completed, got %v", params.Status)
	}
}

func TestRPCMessageUnmarshalError(t *testing.T) {
	raw := `{"jsonrpc":"2.0","method":"on_error","params":{"message":"something failed"}}`
	var msg RPCMessage
	json.Unmarshal([]byte(raw), &msg)

	var params ErrorParams
	json.Unmarshal(msg.Params, &params)
	if params.Message != "something failed" {
		t.Errorf("expected message=something failed, got %v", params.Message)
	}
}

func TestRPCMessageUnmarshalStatus(t *testing.T) {
	raw := `{"jsonrpc":"2.0","method":"on_status","params":{"model":"qwen3:8b","provider":"ollama","mode":"suggest","session_id":"abc123"}}`
	var msg RPCMessage
	json.Unmarshal([]byte(raw), &msg)

	var params StatusParams
	json.Unmarshal(msg.Params, &params)
	if params.Model != "qwen3:8b" {
		t.Errorf("expected model=qwen3:8b, got %v", params.Model)
	}
	if params.Provider != "ollama" {
		t.Errorf("expected provider=ollama, got %v", params.Provider)
	}
	if params.Mode != "suggest" {
		t.Errorf("expected mode=suggest, got %v", params.Mode)
	}
}

func TestRPCMessageUnmarshalAskUser(t *testing.T) {
	raw := `{"jsonrpc":"2.0","id":1001,"method":"on_ask_user","params":{"question":"Which option?","options":["A","B","C"],"allow_text":true}}`
	var msg RPCMessage
	json.Unmarshal([]byte(raw), &msg)

	var params AskUserRequestParams
	json.Unmarshal(msg.Params, &params)
	if params.Question != "Which option?" {
		t.Errorf("expected question=Which option?, got %v", params.Question)
	}
	if len(params.Options) != 3 {
		t.Errorf("expected 3 options, got %d", len(params.Options))
	}
	if !params.AllowText {
		t.Error("expected allow_text=true")
	}
}

func TestRPCMessageUnmarshalErrorField(t *testing.T) {
	raw := `{"jsonrpc":"2.0","id":1,"error":{"code":-32601,"message":"Method not found"}}`
	var msg RPCMessage
	json.Unmarshal([]byte(raw), &msg)

	if msg.Error == nil {
		t.Fatal("expected error field")
	}
	if msg.Error.Code != -32601 {
		t.Errorf("expected code=-32601, got %d", msg.Error.Code)
	}
	if msg.Error.Message != "Method not found" {
		t.Errorf("expected message=Method not found, got %v", msg.Error.Message)
	}
}

// --- Round-trip tests ---

func TestChatParamsRoundTrip(t *testing.T) {
	orig := ChatParams{Message: "hello world", SessionID: "sess-123"}
	data, _ := json.Marshal(orig)
	var decoded ChatParams
	json.Unmarshal(data, &decoded)
	if decoded.Message != orig.Message || decoded.SessionID != orig.SessionID {
		t.Errorf("round-trip mismatch: %+v != %+v", decoded, orig)
	}
}

func TestApprovalResultRoundTrip(t *testing.T) {
	orig := ApprovalResult{Approved: true, SessionApprove: true}
	data, _ := json.Marshal(orig)
	var decoded ApprovalResult
	json.Unmarshal(data, &decoded)
	if decoded.Approved != orig.Approved || decoded.SessionApprove != orig.SessionApprove {
		t.Errorf("round-trip mismatch: %+v != %+v", decoded, orig)
	}
}

func TestAskUserResultRoundTrip(t *testing.T) {
	orig := AskUserResult{Answer: "Option B"}
	data, _ := json.Marshal(orig)
	var decoded AskUserResult
	json.Unmarshal(data, &decoded)
	if decoded.Answer != orig.Answer {
		t.Errorf("round-trip mismatch: %+v != %+v", decoded, orig)
	}
}

func TestSessionResumeParamsRoundTrip(t *testing.T) {
	orig := SessionResumeParams{SessionID: "abc-def-123"}
	data, _ := json.Marshal(orig)
	var decoded SessionResumeParams
	json.Unmarshal(data, &decoded)
	if decoded.SessionID != orig.SessionID {
		t.Errorf("round-trip mismatch: %+v != %+v", decoded, orig)
	}
}

func TestDoneParamsWithCancelled(t *testing.T) {
	raw := `{"tokens_in":50,"tokens_out":100,"cancelled":true}`
	var params DoneParams
	json.Unmarshal([]byte(raw), &params)
	if params.TokensIn != 50 || params.TokensOut != 100 || !params.Cancelled {
		t.Errorf("unexpected: %+v", params)
	}
}

func TestDoneParamsWithoutCancelled(t *testing.T) {
	raw := `{"tokens_in":50,"tokens_out":100}`
	var params DoneParams
	json.Unmarshal([]byte(raw), &params)
	if params.Cancelled {
		t.Error("expected cancelled=false by default")
	}
}

// --- SessionListResult tests ---

func TestSessionListResultUnmarshal(t *testing.T) {
	raw := `{"sessions":[{"id":"abc-123","title":"My session","model":"qwen3:8b","provider":"ollama"},{"id":"def-456","title":"Another","model":"gpt-4","provider":"openrouter"}]}`
	var result SessionListResult
	if err := json.Unmarshal([]byte(raw), &result); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if len(result.Sessions) != 2 {
		t.Fatalf("expected 2 sessions, got %d", len(result.Sessions))
	}
	if result.Sessions[0].ID != "abc-123" {
		t.Errorf("expected id=abc-123, got %s", result.Sessions[0].ID)
	}
	if result.Sessions[0].Title != "My session" {
		t.Errorf("expected title=My session, got %s", result.Sessions[0].Title)
	}
	if result.Sessions[0].Model != "qwen3:8b" {
		t.Errorf("expected model=qwen3:8b, got %s", result.Sessions[0].Model)
	}
	if result.Sessions[0].Provider != "ollama" {
		t.Errorf("expected provider=ollama, got %s", result.Sessions[0].Provider)
	}
	if result.Sessions[1].ID != "def-456" {
		t.Errorf("expected second id=def-456, got %s", result.Sessions[1].ID)
	}
}

func TestSessionListResultEmpty(t *testing.T) {
	raw := `{"sessions":[]}`
	var result SessionListResult
	if err := json.Unmarshal([]byte(raw), &result); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if len(result.Sessions) != 0 {
		t.Errorf("expected 0 sessions, got %d", len(result.Sessions))
	}
}

func TestSessionInfoFieldsRoundTrip(t *testing.T) {
	orig := SessionInfo{
		ID:       "uuid-1234-5678",
		Title:    "Test Session",
		Model:    "qwen3:8b",
		Provider: "ollama",
	}
	data, err := json.Marshal(orig)
	if err != nil {
		t.Fatalf("marshal error: %v", err)
	}
	var decoded SessionInfo
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if decoded.ID != orig.ID {
		t.Errorf("ID mismatch: %s != %s", decoded.ID, orig.ID)
	}
	if decoded.Title != orig.Title {
		t.Errorf("Title mismatch: %s != %s", decoded.Title, orig.Title)
	}
	if decoded.Model != orig.Model {
		t.Errorf("Model mismatch: %s != %s", decoded.Model, orig.Model)
	}
	if decoded.Provider != orig.Provider {
		t.Errorf("Provider mismatch: %s != %s", decoded.Provider, orig.Provider)
	}
}

func TestSessionListParamsMarshal(t *testing.T) {
	params := SessionListParams{}
	data, err := json.Marshal(params)
	if err != nil {
		t.Fatalf("marshal error: %v", err)
	}
	// Should produce empty JSON object
	if string(data) != "{}" {
		t.Errorf("expected {}, got %s", string(data))
	}
}

func TestSessionListResultMarshal(t *testing.T) {
	result := SessionListResult{
		Sessions: []SessionInfo{
			{ID: "id1", Title: "t1", Model: "m1", Provider: "p1"},
		},
	}
	data, err := json.Marshal(result)
	if err != nil {
		t.Fatalf("marshal error: %v", err)
	}
	var decoded map[string]interface{}
	json.Unmarshal(data, &decoded)
	sessions := decoded["sessions"].([]interface{})
	if len(sessions) != 1 {
		t.Errorf("expected 1 session, got %d", len(sessions))
	}
}

func TestSessionInfoEmptyFields(t *testing.T) {
	raw := `{"id":"x","title":"","model":"","provider":""}`
	var info SessionInfo
	json.Unmarshal([]byte(raw), &info)
	if info.ID != "x" {
		t.Errorf("expected id=x, got %s", info.ID)
	}
	if info.Title != "" {
		t.Errorf("expected empty title, got %s", info.Title)
	}
}
