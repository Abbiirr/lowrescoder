package main

import (
	"os"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/textarea"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// stage represents the current UI state.
type stage int

const (
	stageInit           stage = iota // Waiting for backend status
	stageInput                       // Ready for user input
	stageStreaming                   // Streaming response from backend
	stageApproval                    // Showing approval prompt
	stageAskUser                     // Showing ask-user prompt
	stageModelPicker                 // Showing model picker after /model
	stageProviderPicker              // Showing provider picker after /provider
)

// toolCallEntry tracks a tool call for the current turn.
type toolCallEntry struct {
	Name   string
	Status string
	Result string
	Args   string
}

// model is the root Bubble Tea model.
type model struct {
	// Components
	composer  textarea.Model
	statusBar statusBarModel
	spin      spinner.Model

	// State
	stage       stage
	backend     *Backend
	width       int
	height      int
	quitting    bool
	claudeLike  bool // claude_like profile gate — enables composer frame

	// Streaming buffers (pointers to avoid copy-by-value panic)
	tokenBuf     *strings.Builder // Raw tokens accumulate here
	streamBuf    *strings.Builder // Flushed content for display
	thinkingBuf  *strings.Builder // Thinking tokens
	streamDirty  bool             // Whether tokenBuf has unflushed content
	showThinking bool

	// Tool calls for current turn
	toolCalls []toolCallEntry

	// Approval state
	approvalRequestID int
	approvalTool      string
	approvalArgs      string
	approvalOptions   []string
	approvalCursor    int

	// Ask-user state
	askRequestID int
	askQuestion  string
	askOptions   []string
	askCursor    int
	askAllowText bool

	// Task panel state
	taskPanelTasks     []taskEntry
	taskPanelSubagents []subagentEntry

	// Message queue
	messageQueue []string
	queueMax     int

	// Interrupt state
	interruptCount int

	// Error display
	lastError string

	// Autocomplete dropdown items (for rendering when >1 match)
	completions       []string
	completionCursor  int // cursor index into completions for Up/Down navigation

	// Model picker state (opened from /model)
	modelPickerEntries []string
	modelPickerCursor  int
	modelPickerCurrent string // model that was active when the picker opened

	// Provider picker state (opened from /provider)
	providerPickerEntries []string
	providerPickerCursor  int
	providerPickerCurrent string // provider that was active when the picker opened

	// Session picker state
	sessionPickerEntries []sessionEntry
}

// initialModel creates the initial model state.
func initialModel(backend *Backend) model {
	sp := spinner.New()
	sp.Spinner = spinner.MiniDot
	sp.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("243"))

	// Gate composer frame behind claude_like profile
	claudeLike := os.Getenv("AUTOCODE_PROFILE") == "claude_like"

	return model{
		composer:   newComposer(60),
		claudeLike: claudeLike,
		statusBar: statusBarModel{
			Model: "...",
			Mode:  "suggest",
		},
		spin:            sp,
		stage:           stageInit,
		backend:         backend,
		tokenBuf:        &strings.Builder{},
		streamBuf:       &strings.Builder{},
		thinkingBuf:     &strings.Builder{},
		showThinking:    true,
		approvalOptions: []string{"Yes", "Yes, this session", "No"},
		queueMax:        10,
	}
}

// Init returns the initial commands.
func (m model) Init() tea.Cmd {
	return tea.Batch(
		textarea.Blink,
		m.spin.Tick,
	)
}

// tickCmd returns a command that sends a tickMsg after 16ms (60fps).
func tickCmd() tea.Cmd {
	return tea.Tick(16*time.Millisecond, func(t time.Time) tea.Msg {
		return tickMsg{Time: t}
	})
}
