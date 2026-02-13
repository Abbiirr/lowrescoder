package main

import "encoding/json"

// --- JSON-RPC wire types ---

// RPCMessage is the union type for all JSON-RPC messages on the wire.
// If ID is nil and Method is set, it's a notification (Python->Go).
// If ID is set and Method is set, it's a request.
// If ID is set and Method is empty, it's a response.
type RPCMessage struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      *int            `json:"id,omitempty"`
	Method  string          `json:"method,omitempty"`
	Params  json.RawMessage `json:"params,omitempty"`
	Result  json.RawMessage `json:"result,omitempty"`
	Error   *RPCError       `json:"error,omitempty"`
}

// RPCRequest is sent from Go to Python.
type RPCRequest struct {
	JSONRPC string      `json:"jsonrpc"`
	ID      int         `json:"id"`
	Method  string      `json:"method"`
	Params  interface{} `json:"params"`
}

// RPCResponse is sent from Go to Python (for approval/ask_user answers).
type RPCResponse struct {
	JSONRPC string      `json:"jsonrpc"`
	ID      int         `json:"id"`
	Result  interface{} `json:"result"`
}

// RPCError represents a JSON-RPC error.
type RPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// --- Notification param types (Python -> Go) ---

// TokenParams carries a streaming text token.
type TokenParams struct {
	Text string `json:"text"`
}

// ThinkingParams carries a thinking/reasoning token.
type ThinkingParams struct {
	Text string `json:"text"`
}

// DoneParams signals end of a generation turn.
type DoneParams struct {
	TokensIn  int  `json:"tokens_in"`
	TokensOut int  `json:"tokens_out"`
	Cancelled bool `json:"cancelled,omitempty"`
	LayerUsed int  `json:"layer_used,omitempty"`
}

// ToolCallParams carries tool call status updates.
type ToolCallParams struct {
	Name   string `json:"name"`
	Status string `json:"status"`
	Result string `json:"result,omitempty"`
	Args   string `json:"args,omitempty"`
}

// ErrorParams carries an error message from the backend.
type ErrorParams struct {
	Message string `json:"message"`
}

// StatusParams carries backend status information.
type StatusParams struct {
	Model     string `json:"model"`
	Provider  string `json:"provider"`
	Mode      string `json:"mode"`
	SessionID string `json:"session_id,omitempty"`
}

// --- Request param types (Python -> Go, with ID) ---

// ApprovalRequestParams is sent when the backend needs tool approval.
type ApprovalRequestParams struct {
	Tool string `json:"tool"`
	Args string `json:"args"`
}

// AskUserRequestParams is sent when the backend needs user input.
type AskUserRequestParams struct {
	Question  string   `json:"question"`
	Options   []string `json:"options,omitempty"`
	AllowText bool     `json:"allow_text,omitempty"`
}

// --- Response types (Go -> Python) ---

// ApprovalResult is the response to an approval request.
type ApprovalResult struct {
	Approved       bool `json:"approved"`
	SessionApprove bool `json:"session_approve,omitempty"`
}

// AskUserResult is the response to an ask_user request.
type AskUserResult struct {
	Answer string `json:"answer"`
}

// --- Go -> Python request params ---

// ChatParams sends a user message to the backend.
type ChatParams struct {
	Message   string `json:"message"`
	SessionID string `json:"session_id,omitempty"`
}

// CancelParams requests cancellation of the current generation.
type CancelParams struct{}

// CommandParams sends a slash command to the backend.
type CommandParams struct {
	Cmd string `json:"cmd"`
}

// SessionNewParams creates a new session.
type SessionNewParams struct {
	Title string `json:"title,omitempty"`
}

// SessionResumeParams resumes an existing session.
type SessionResumeParams struct {
	SessionID string `json:"session_id"`
}

// ConfigSetParams sets a configuration value.
type ConfigSetParams struct {
	Key   string `json:"key"`
	Value string `json:"value"`
}

// SessionListParams requests the list of available sessions.
type SessionListParams struct{}

// SessionListResult is the response from session.list.
type SessionListResult struct {
	Sessions []SessionInfo `json:"sessions"`
}

// SessionInfo describes a single session entry.
type SessionInfo struct {
	ID       string `json:"id"`
	Title    string `json:"title"`
	Model    string `json:"model"`
	Provider string `json:"provider"`
}
