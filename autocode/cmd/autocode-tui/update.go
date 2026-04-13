package main

import (
	"encoding/json"
	"strings"

	"github.com/charmbracelet/bubbles/spinner"
	tea "github.com/charmbracelet/bubbletea"
)

// Update handles all messages for the root model.
func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {

	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		composerSetWidth(&m.composer, msg.Width)
		m.statusBar.Width = msg.Width
		// Force an immediate render cycle so spinner/tool rows/status
		// pick up the new width without waiting for the next streaming
		// tick. Fixes Codex Entry 1071 blocker #2: resize stayed on
		// stale-width formatting partway through a stream.
		return m, tickCmd()

	case tea.KeyMsg:
		switch m.stage {
		case stageInput, stageInit:
			return m.handleInputKey(msg)
		case stageStreaming:
			return m.handleStreamingKey(msg)
		case stageApproval:
			return handleApprovalKey(m, msg)
		case stageAskUser:
			return handleAskUserKey(m, msg)
		case stageModelPicker:
			return handleModelPickerKey(m, msg)
		case stageProviderPicker:
			return handleProviderPickerKey(m, msg)
		case stagePalette:
			return m.handlePaletteKey(msg)
		}

	case backendStatusMsg:
		m.statusBar.Model = msg.Model
		m.statusBar.Provider = msg.Provider
		m.statusBar.Mode = msg.Mode
		if m.stage == stageInit {
			m.stage = stageInput
		}
		return m, nil

	case backendTokenMsg:
		if m.stage != stageStreaming {
			// Not streaming (for example slash-command output): preserve formatting
			// and print directly to scrollback.
			if msg.Text == "" {
				return m, nil
			}
			return m, tea.Printf("%s", msg.Text)
		}
		m.tokenBuf.WriteString(msg.Text)
		if !m.streamDirty {
			m.streamDirty = true
			return m, tickCmd()
		}
		return m, nil

	case backendThinkingMsg:
		m.thinkingBuf.WriteString(msg.Text)
		// Trigger a tick to force view refresh for live thinking display
		if !m.streamDirty {
			m.streamDirty = true
			return m, tickCmd()
		}
		return m, nil

	case backendToolCallMsg:
		m.updateToolCall(msg)
		return m, nil

	case backendDoneMsg:
		return m.handleDone(msg)

	case backendErrorMsg:
		m.lastError = msg.Message
		return m, nil

	case backendApprovalRequestMsg:
		return enterApproval(m, msg), nil

	case backendAskUserRequestMsg:
		return enterAskUser(m, msg), nil

	case backendSessionListMsg:
		if len(msg.Sessions) == 0 {
			m.lastError = "No sessions found"
			return m, nil
		}
		return enterSessionPicker(m, msg), nil

	case backendModelListMsg:
		if len(msg.Models) == 0 {
			m.lastError = "No models returned from backend"
			return m, nil
		}
		return enterModelPicker(m, msg.Models, msg.Current), nil

	case backendProviderListMsg:
		if len(msg.Providers) == 0 {
			m.lastError = "No providers returned from backend"
			return m, nil
		}
		return enterProviderPicker(m, msg.Providers, msg.Current), nil

	case backendTaskStateMsg:
		m.taskPanelTasks = msg.Tasks
		m.taskPanelSubagents = msg.Subagents
		return m, nil

	case backendExitMsg:
		m.quitting = true
		return m, tea.Quit

	case tickMsg:
		if m.streamDirty {
			// Flush token buffer to stream buffer
			m.streamBuf.WriteString(m.tokenBuf.String())
			m.tokenBuf.Reset()
			m.streamDirty = false
		}
		return m, nil

	case queueDrainMsg:
		if len(m.messageQueue) > 0 {
			next := m.messageQueue[0]
			m.messageQueue = m.messageQueue[1:]
			return m.sendChat(next)
		}
		return m, nil

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spin, cmd = m.spin.Update(msg)
		// Rotate spinner verb every ~3 seconds
		if m.stage == stageStreaming {
			m.verbTicks++
			if m.verbTicks >= 8 { // spinner ticks ~2.5x/sec with MiniDot
				m.verbTicks = 0
				m.currentVerb = randomVerb()
			}
		}
		return m, cmd
	}

	// Forward unhandled messages to composer (cursor blink, etc.)
	if m.stage == stageInput || m.stage == stageInit || m.stage == stageStreaming {
		var cmd tea.Cmd
		m.composer, cmd = m.composer.Update(msg)
		return m, cmd
	}

	return m, nil
}

// handleInputKey handles key events during input stage.
func (m model) handleInputKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "ctrl+c":
		m.interruptCount++
		if m.interruptCount >= 2 {
			m.quitting = true
			return m, tea.Quit
		}
		m.lastError = "Press Ctrl+C again to quit, or Ctrl+D"
		return m, nil

	case "ctrl+d":
		m.quitting = true
		return m, tea.Quit

	case "ctrl+k":
		m.stage = stagePalette
		m.paletteFilter = ""
		m.paletteCursor = 0
		m.paletteMatches = filterPaletteCommands("")
		return m, nil

	case "enter":
		// Slash menu: Enter accepts the highlighted completion instead of submitting
		if len(m.completions) > 1 {
			if m.completionCursor < 0 || m.completionCursor >= len(m.completions) {
				m.completionCursor = 0
			}
			m.composer.SetValue(m.completions[m.completionCursor])
			m.completions = nil
			m.completionCursor = 0
			return m, nil
		}
		// Auto-accept single completion
		if len(m.completions) == 1 {
			m.composer.SetValue(m.completions[0])
		}

		text := composerValue(&m)
		if text == "" {
			return m, nil
		}
		composerClear(&m)
		m.completions = nil
		m.completionCursor = 0
		m.interruptCount = 0
		m.lastError = ""

		// /model (with no arg) → open model picker, not text dump
		if text == "/model" || text == "/m" {
			if m.backend != nil {
				return m, requestModelListCmd(m.backend)
			}
			return m, tea.Println(errorStyle.Render("Backend not connected — /model picker requires the Python backend"))
		}

		// /provider (with no arg) → open provider picker, not text dump
		if text == "/provider" {
			if m.backend != nil {
				return m, requestProviderListCmd(m.backend)
			}
			return m, tea.Println(errorStyle.Render("Backend not connected — /provider picker requires the Python backend"))
		}

		// Handle slash commands locally or delegate
		if strings.HasPrefix(text, "/") {
			return m.handleSlashCommand(text)
		}

		return m.sendChat(text)

	case "escape", "esc":
		// Escape closes the slash menu cleanly
		if len(m.completions) > 0 {
			m.completions = nil
			m.completionCursor = 0
			return m, nil
		}
		return m, nil

	case "tab":
		// Tab accepts the highlighted (or first) completion
		if len(m.completions) > 0 {
			idx := m.completionCursor
			if idx < 0 || idx >= len(m.completions) {
				idx = 0
			}
			m.composer.SetValue(m.completions[idx])
			m.completions = nil
			m.completionCursor = 0
		}
		return m, nil

	case "up":
		// Slash menu: Up moves the highlight up
		if len(m.completions) > 1 {
			m.completionCursor--
			if m.completionCursor < 0 {
				m.completionCursor = len(m.completions) - 1
			}
			return m, nil
		}
		// History when single-line, textarea navigation when multi-line
		if m.composer.LineCount() <= 1 {
			prev := historyPrevious()
			if prev != "" {
				m.composer.SetValue(prev)
			}
			return m, nil
		}
		var cmd tea.Cmd
		m.composer, cmd = m.composer.Update(msg)
		return m, cmd

	case "down":
		// Slash menu: Down moves the highlight down
		if len(m.completions) > 1 {
			m.completionCursor++
			if m.completionCursor >= len(m.completions) {
				m.completionCursor = 0
			}
			return m, nil
		}
		if m.composer.LineCount() <= 1 {
			next := historyNext()
			m.composer.SetValue(next)
			return m, nil
		}
		var cmd tea.Cmd
		m.composer, cmd = m.composer.Update(msg)
		return m, cmd

	default:
		var cmd tea.Cmd
		m.composer, cmd = m.composer.Update(msg)
		m.updateCompletions()
		composerAutoHeight(&m)
		return m, cmd
	}
}

// handleStreamingKey handles key events during streaming.
func (m model) handleStreamingKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "ctrl+d":
		// Force quit from streaming
		m.quitting = true
		return m, tea.Quit

	case "ctrl+c":
		// Double Ctrl+C force quits; single cancels generation
		m.interruptCount++
		if m.interruptCount >= 2 {
			m.quitting = true
			return m, tea.Quit
		}
		// Cancel generation + clear queue
		m.messageQueue = nil
		if m.backend != nil {
			m.backend.SendRequest("cancel", CancelParams{})
		}
		return m, nil

	case "escape", "esc":
		// Cancel generation + clear queue
		m.messageQueue = nil
		if m.backend != nil {
			m.backend.SendRequest("cancel", CancelParams{})
		}
		return m, nil

	case "enter":
		// Queue message during streaming
		text := composerValue(&m)
		if text != "" && len(m.messageQueue) < m.queueMax {
			m.messageQueue = append(m.messageQueue, text)
			composerClear(&m)
		}
		return m, nil

	default:
		// Allow typing while streaming (parallel input)
		var cmd tea.Cmd
		m.composer, cmd = m.composer.Update(msg)
		composerAutoHeight(&m)
		return m, cmd
	}
}

// sendChat sends a chat message to the backend.
func (m model) sendChat(text string) (tea.Model, tea.Cmd) {
	// Add to history
	historyAdd(text)

	// Echo user turn to scrollback
	echoCmd := tea.Println(userTurnStyle.Render("You: ") + text)

	// Reset per-turn state
	m.streamBuf.Reset()
	m.tokenBuf.Reset()
	m.thinkingBuf.Reset()
	m.toolCalls = nil
	m.lastError = ""
	m.streamDirty = false
	m.interruptCount = 0
	m.currentVerb = randomVerb()
	m.verbTicks = 0

	// Send to backend — keep composer focused for parallel typing
	m.stage = stageStreaming
	if m.backend != nil {
		m.backend.SendRequest("chat", ChatParams{
			Message:   text,
			SessionID: "",
		})
	}

	return m, echoCmd
}

// handleDone processes the end of a generation turn.
func (m model) handleDone(msg backendDoneMsg) (tea.Model, tea.Cmd) {
	// Flush any remaining tokens
	if m.tokenBuf.Len() > 0 {
		m.streamBuf.WriteString(m.tokenBuf.String())
		m.tokenBuf.Reset()
	}

	// Update stats
	m.statusBar.Tokens += msg.TokensIn + msg.TokensOut

	// Build scrollback output
	var cmds []tea.Cmd

	// Tool calls summary — same compact ⎿ format as live view
	for _, tc := range m.toolCalls {
		icon := toolIcon(tc.Status)
		line := " \u23bf " + icon + " " + toolCallStyle.Render(tc.Name)
		if tc.Status == "error" && tc.Result != "" {
			line += " " + errorStyle.Render(tc.Result)
		} else if tc.Result != "" {
			result := tc.Result
			if len(result) > 100 {
				result = result[:97] + "..."
			}
			line += " " + dimStyle.Render(result)
		}
		cmds = append(cmds, tea.Println(line))
	}

	// Render markdown content via Glamour ONCE on done
	content := m.streamBuf.String()
	if content != "" {
		rendered := renderMarkdownContent(content, m.width)
		cmds = append(cmds, tea.Println(rendered))
	}

	// Separator
	cmds = append(cmds, tea.Println(separator(m.width)))

	// Reset per-turn state
	m.streamBuf.Reset()
	m.thinkingBuf.Reset()
	m.toolCalls = nil
	m.streamDirty = false
	m.stage = stageInput
	composerFocus(&m)

	// Drain queue if messages pending
	if len(m.messageQueue) > 0 {
		cmds = append(cmds, func() tea.Msg { return queueDrainMsg{} })
	}

	return m, tea.Batch(cmds...)
}

// handleSlashCommand processes Go-local commands or delegates to Python.
func (m model) handleSlashCommand(text string) (tea.Model, tea.Cmd) {
	cmd, args := parseCommand(text)

	switch cmd {
	case "exit", "quit", "q":
		m.quitting = true
		return m, tea.Quit

	case "clear", "cls":
		return m, tea.ClearScreen

	case "thinking", "think":
		m.showThinking = !m.showThinking
		state := "off"
		if m.showThinking {
			state = "on"
		}
		return m, tea.Println(dimStyle.Render("Thinking: " + state))

	case "resume":
		if m.backend == nil {
			return m, tea.Println(errorStyle.Render("Backend not connected \u2014 /resume requires the Python backend"))
		}
		args = strings.TrimSpace(args)
		if args != "" {
			// Direct resume with session ID
			return m, sessionResumeCmd(m.backend, args)
		}
		// No args: fetch session list and show picker
		return m, m.backend.SendRequestCmd("session.list", SessionListParams{}, func(result json.RawMessage, rpcErr *RPCError) tea.Msg {
			if rpcErr != nil {
				return backendErrorMsg{Message: "session.list failed: " + rpcErr.Message}
			}
			var listResult SessionListResult
			if err := json.Unmarshal(result, &listResult); err != nil {
				return backendErrorMsg{Message: "failed to parse session list: " + err.Error()}
			}
			sessions := make([]sessionEntry, len(listResult.Sessions))
			for i, s := range listResult.Sessions {
				sessions[i] = sessionEntry{
					ID:       s.ID,
					Title:    s.Title,
					Model:    s.Model,
					Provider: s.Provider,
				}
			}
			return backendSessionListMsg{Sessions: sessions}
		})

	default:
		// Delegate to Python backend
		if m.backend != nil {
			m.backend.SendRequest("command", CommandParams{Cmd: text})
			return m, nil
		}
		return m, tea.Println(errorStyle.Render("Backend not connected \u2014 " + text + " requires the Python backend"))
	}
}

// updateToolCall updates or appends a tool call entry.
func (m *model) updateToolCall(msg backendToolCallMsg) {
	// Update existing entry if found
	for i := range m.toolCalls {
		if m.toolCalls[i].Name == msg.Name && m.toolCalls[i].Status == "running" {
			m.toolCalls[i].Status = msg.Status
			m.toolCalls[i].Result = msg.Result
			return
		}
	}
	// Append new entry
	m.toolCalls = append(m.toolCalls, toolCallEntry{
		Name:   msg.Name,
		Status: msg.Status,
		Result: msg.Result,
		Args:   msg.Args,
	})
}

// updateCompletions refreshes autocomplete suggestions based on current input.
func (m *model) updateCompletions() {
	text := m.composer.Value()
	// Only offer completions for single-line slash commands
	if strings.Contains(text, "\n") {
		m.completions = nil
		m.completionCursor = 0
		return
	}
	completions := getCompletions(text)
	// Reset cursor whenever the completion list changes
	if len(completions) != len(m.completions) {
		m.completionCursor = 0
	} else {
		for i := range completions {
			if completions[i] != m.completions[i] {
				m.completionCursor = 0
				break
			}
		}
	}
	m.completions = completions
}

// --- Command palette ---

var paletteEntries = []struct {
	Cmd  string
	Desc string
}{
	{"/help", "Show help and available commands"},
	{"/new", "Start a new session"},
	{"/sessions", "List and switch sessions"},
	{"/resume", "Resume a previous session"},
	{"/model", "Switch the LLM model"},
	{"/provider", "Switch the LLM provider"},
	{"/mode", "Change approval mode"},
	{"/compact", "Compact conversation to save tokens"},
	{"/build", "Run build / agent loop"},
	{"/loop", "Run agent loop with custom iterations"},
	{"/research", "Deep research mode"},
	{"/review", "Code review mode"},
	{"/tasks", "Show task board"},
	{"/plan", "Plan mode controls"},
	{"/memory", "Show learned patterns"},
	{"/checkpoint", "Manage checkpoints"},
	{"/thinking", "Toggle thinking display"},
	{"/shell", "Toggle shell execution"},
	{"/init", "Initialize project context"},
	{"/index", "Build code search index"},
	{"/copy", "Copy last response to clipboard"},
	{"/clear", "Clear the screen"},
	{"/exit", "Quit AutoCode"},
}

func filterPaletteCommands(filter string) []string {
	filter = strings.ToLower(strings.TrimSpace(filter))
	var matches []string
	for _, e := range paletteEntries {
		if filter == "" ||
			strings.Contains(strings.ToLower(e.Cmd), filter) ||
			strings.Contains(strings.ToLower(e.Desc), filter) {
			matches = append(matches, e.Cmd)
		}
	}
	return matches
}

func paletteDescMap() map[string]string {
	m := make(map[string]string, len(paletteEntries))
	for _, e := range paletteEntries {
		m[e.Cmd] = e.Desc
	}
	return m
}

func (m model) handlePaletteKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "escape", "esc", "ctrl+k":
		m.stage = stageInput
		composerFocus(&m)
		return m, nil

	case "enter":
		if len(m.paletteMatches) > 0 && m.paletteCursor < len(m.paletteMatches) {
			selected := m.paletteMatches[m.paletteCursor]
			m.stage = stageInput
			composerFocus(&m)
			m.composer.SetValue(selected + " ")
			return m, nil
		}
		m.stage = stageInput
		composerFocus(&m)
		return m, nil

	case "up":
		if m.paletteCursor > 0 {
			m.paletteCursor--
		}
		return m, nil

	case "down":
		if m.paletteCursor < len(m.paletteMatches)-1 {
			m.paletteCursor++
		}
		return m, nil

	case "backspace":
		if len(m.paletteFilter) > 0 {
			m.paletteFilter = m.paletteFilter[:len(m.paletteFilter)-1]
			m.paletteMatches = filterPaletteCommands(m.paletteFilter)
			m.paletteCursor = 0
		}
		return m, nil

	default:
		r := msg.String()
		if len(r) == 1 {
			m.paletteFilter += r
			m.paletteMatches = filterPaletteCommands(m.paletteFilter)
			m.paletteCursor = 0
		}
		return m, nil
	}
}
