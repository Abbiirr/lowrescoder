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

// backendModelListMsg carries the list of available models from the backend.
type backendModelListMsg struct {
	Models  []string
	Current string
}

// backendProviderListMsg carries the list of supported providers from the backend.
type backendProviderListMsg struct {
	Providers []string
	Current   string
}

// taskEntry represents a task in the task panel.
type taskEntry struct {
	ID     string `json:"id"`
	Title  string `json:"title"`
	Status string `json:"status"`
}

// subagentEntry represents a subagent in the task panel.
type subagentEntry struct {
	ID      string `json:"id"`
	Type    string `json:"type"`
	Status  string `json:"status"`
	Summary string `json:"summary"`
}

// backendTaskStateMsg carries task and subagent state from the backend.
type backendTaskStateMsg struct {
	Tasks     []taskEntry
	Subagents []subagentEntry
}

// startupTimeoutMsg fires when the backend has not sent backendStatusMsg
// within the startup timeout. Transitions stageInit → stageInput with an
// error so the TUI is usable even when the backend is slow to start.
type startupTimeoutMsg struct{}

// --- Phase 4: Steer / Followup / Fork messages ---

// steerSendMsg is sent when the user confirms a steer message.
type steerSendMsg struct {
	Text string
}

// followupDrainMsg processes the next followup message.
type followupDrainMsg struct{}

// backendForkResultMsg carries the result of a fork_session RPC.
type backendForkResultMsg struct {
	NewSessionID string
	Error        string
}

// --- Phase 5: Editor / Theme messages ---

// editorDoneMsg is sent when the external editor closes.
type editorDoneMsg struct {
	Content string
}

// bgColorMsg carries the detected terminal background color.
type bgColorMsg struct {
	R, G, B int
}

// backendWarningMsg carries a backend stderr line classified as WARNING severity.
// Rendered in dim yellow rather than the red error banner.
type backendWarningMsg struct {
	Message string
}

// --- Phase 6: Cost / Token messages ---

// backendCostMsg carries a cost update from the backend.
type backendCostMsg struct {
	Cost      string
	TokensIn  int
	TokensOut int
}

// backendSessionIDMsg carries the session ID from the backend.
type backendSessionIDMsg struct {
	SessionID string
}
