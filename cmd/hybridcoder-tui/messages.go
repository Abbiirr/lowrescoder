package main

import "time"

// All custom tea.Msg types that the reader goroutine sends into the Update loop.

// backendTokenMsg carries a streaming text token from the backend.
type backendTokenMsg struct {
	Text string
}

// backendThinkingMsg carries a thinking/reasoning token.
type backendThinkingMsg struct {
	Text string
}

// backendDoneMsg signals the end of a generation turn.
type backendDoneMsg struct {
	TokensIn  int
	TokensOut int
	Cancelled bool
	LayerUsed int
}

// backendToolCallMsg carries a tool call status update.
type backendToolCallMsg struct {
	Name   string
	Status string
	Result string
	Args   string
}

// backendErrorMsg carries an error from the backend.
type backendErrorMsg struct {
	Message string
}

// backendStatusMsg carries status updates (model, provider, mode, session).
type backendStatusMsg struct {
	Model     string
	Provider  string
	Mode      string
	SessionID string
}

// backendApprovalRequestMsg is sent when the backend needs tool approval.
type backendApprovalRequestMsg struct {
	RequestID int
	Tool      string
	Args      string
}

// backendAskUserRequestMsg is sent when the backend needs user input.
type backendAskUserRequestMsg struct {
	RequestID int
	Question  string
	Options   []string
	AllowText bool
}

// backendExitMsg signals that the backend process has exited.
type backendExitMsg struct {
	Err error
}

// tickMsg is sent periodically for streaming buffer flushes.
type tickMsg struct {
	Time time.Time
}

// queueDrainMsg triggers processing the next queued message.
type queueDrainMsg struct{}

// sessionEntry represents a session in the picker list.
type sessionEntry struct {
	ID       string
	Title    string
	Model    string
	Provider string
}

// backendSessionListMsg carries the list of sessions from the backend.
type backendSessionListMsg struct {
	Sessions []sessionEntry
}
