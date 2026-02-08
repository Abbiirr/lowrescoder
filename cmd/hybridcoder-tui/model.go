package main

import (
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// stage represents the current UI state.
type stage int

const (
	stageInit      stage = iota // Waiting for backend status
	stageInput                  // Ready for user input
	stageStreaming              // Streaming response from backend
	stageApproval               // Showing approval prompt
	stageAskUser                // Showing ask-user prompt
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
	textInput textinput.Model
	statusBar statusBarModel
	spin      spinner.Model

	// State
	stage    stage
	backend  *Backend
	width    int
	height   int
	quitting bool

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

	// Message queue
	messageQueue []string
	queueMax     int

	// Interrupt state
	interruptCount int

	// Error display
	lastError string

	// Autocomplete dropdown items (for rendering when >1 match)
	completions []string

	// Session picker state
	sessionPickerEntries []sessionEntry
}

// initialModel creates the initial model state.
func initialModel(backend *Backend) model {
	ti := textinput.New()
	ti.Placeholder = "Type a message..."
	ti.Focus()
	ti.CharLimit = 2000
	ti.Width = 60
	ti.ShowSuggestions = true
	ti.CompletionStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("240"))
	// Disable Up/Down for suggestion cycling — they're used for history navigation
	ti.KeyMap.NextSuggestion.SetEnabled(false)
	ti.KeyMap.PrevSuggestion.SetEnabled(false)

	sp := spinner.New()
	sp.Spinner = spinner.Dot
	sp.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))

	return model{
		textInput: ti,
		statusBar: statusBarModel{
			Model:    "...",
			Provider: "...",
			Mode:     "suggest",
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
		textinput.Blink,
		m.spin.Tick,
	)
}

// tickCmd returns a command that sends a tickMsg after 16ms (60fps).
func tickCmd() tea.Cmd {
	return tea.Tick(16*time.Millisecond, func(t time.Time) tea.Msg {
		return tickMsg{Time: t}
	})
}
