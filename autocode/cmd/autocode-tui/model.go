package main

import (
	"os"
	"strings"
	"time"

	"charm.land/bubbles/v2/spinner"
	"charm.land/bubbles/v2/textarea"
	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"
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
	stagePalette                     // Showing command palette (Ctrl+K)
	stageSteer                       // Phase 4: typing a steer message
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
	stage      stage
	backend    *Backend
	width      int
	height     int
	quitting   bool
	inlineMode bool // --inline flag: scrollback-friendly, no alternate screen
	claudeLike bool // claude_like profile gate — enables composer frame

	// Streaming buffers (pointers to avoid copy-by-value panic)
	tokenBuf     *strings.Builder // Raw tokens accumulate here
	streamBuf    *strings.Builder // Flushed content for display
	thinkingBuf  *strings.Builder // Thinking tokens
	streamDirty  bool             // Whether tokenBuf has unflushed content
	showThinking bool

	// Spinner verb rotation (Claude Code style — 187 verbs)
	currentVerb string
	verbTicks   int

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
	completions      []string
	completionCursor int // cursor index into completions for Up/Down navigation

	// Model picker state (opened from /model)
	modelPickerEntries []string
	modelPickerCursor  int
	modelPickerCurrent string // model that was active when the picker opened

	// Provider picker state (opened from /provider)
	providerPickerEntries []string
	providerPickerCursor  int
	providerPickerCurrent string // provider that was active when the picker opened

	// Command palette state (Ctrl+K)
	paletteFilter  string
	paletteCursor  int
	paletteMatches []string

	// Session picker state
	sessionPickerEntries []sessionEntry

	// --- Phase 3: Sliding window streaming ---
	stableScrollbackLines []string // lines flushed to scrollback (never redrawn)
	maxLiveLines          int      // max lines kept in the live stream panel (default 10)

	// --- Phase 4: Steering queue ---
	stageSteer  bool   // true when user pressed Ctrl+C during streaming to type a steer message
	steerInput  string // the steer message being typed
	steerCursor int    // cursor position in steer input

	// --- Phase 4: Follow-up queue ---
	followupQueue []string // messages queued via /followup to send after current tool completes

	// --- Phase 5: Frecency history ---
	promptHistory []historyEntry // frecency-ranked prompt history

	// --- Phase 5: Plan mode ---
	planMode bool // true when in read-only planning mode

	// --- Phase 6: Enhanced status bar ---
	sessionID       string // abbreviated session ID
	totalCost       string // running cost total
	totalTokensIn   int    // input tokens accumulated
	totalTokensOut  int    // output tokens accumulated
	backgroundTasks int    // count of background tasks running
	themeDetected   string // "dark" or "light" from OSC 11 query
	bgColorR        int    // background color R component from OSC 11
	bgColorG        int    // background color G component from OSC 11
	bgColorB        int    // background color B component from OSC 11

	// Benchmark sentinel mode (AUTOCODE_BENCH=1)
	benchMode      bool
	benchReadySent bool
}

// initialModel creates the initial model state.
func initialModel(backend *Backend) model {
	sp := spinner.New(spinner.WithSpinner(spinner.MiniDot), spinner.WithStyle(lipgloss.NewStyle().Foreground(lipgloss.Color("243"))))

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
		currentVerb:     randomVerb(),
		approvalOptions: []string{"Yes", "Yes, this session", "No"},
		queueMax:        10,
		maxLiveLines:    10,
		benchMode:       os.Getenv("AUTOCODE_BENCH") == "1" || os.Getenv("HYBRIDCODER_BENCH") == "1",
	}
}

// startupTimeoutDuration is how long to wait for the backend to send
// its first on_status before giving up and allowing the user to interact.
const startupTimeoutDuration = 15 * time.Second

// startupTimeoutCmd returns a command that fires startupTimeoutMsg after
// startupTimeoutDuration, used to unblock stageInit if backend is slow.
func startupTimeoutCmd() tea.Cmd {
	return tea.Tick(startupTimeoutDuration, func(time.Time) tea.Msg {
		return startupTimeoutMsg{}
	})
}

// Init returns the initial commands.
func (m model) Init() tea.Cmd {
	return tea.Batch(
		textarea.Blink,
		m.spin.Tick,
		startupTimeoutCmd(),
		detectThemeCmd(),
	)
}

// detectThemeCmd detects terminal background theme from environment variables.
// Many terminals set COLORFGBG (e.g., "0;15" = light bg) or TERM_PROGRAM
// which can hint at dark/light mode.
func detectThemeCmd() tea.Cmd {
	return func() tea.Msg {
		colorfgbg := os.Getenv("COLORFGBG")
		if colorfgbg != "" {
			parts := strings.Split(colorfgbg, ";")
			if len(parts) >= 2 {
				bg := parts[len(parts)-1]
				lightBGs := map[string]bool{"15": true, "7": true, "231": true, "255": true, "46": true, "47": true, "48": true, "49": true, "230": true}
				if lightBGs[bg] {
					return bgColorMsg{R: 255, G: 255, B: 255}
				}
			}
		}
		return bgColorMsg{R: 30, G: 30, B: 30}
	}
}

// tickCmd returns a command that sends a tickMsg after 16ms (60fps).
func tickCmd() tea.Cmd {
	return tea.Tick(16*time.Millisecond, func(t time.Time) tea.Msg {
		return tickMsg{Time: t}
	})
}
