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
		m.textInput.Width = msg.Width - 4
		m.statusBar.Width = msg.Width
		return m, nil

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
		return m, cmd
	}

	// Forward unhandled messages to textinput (input mode + streaming for parallel typing)
	if m.stage == stageInput || m.stage == stageInit || m.stage == stageStreaming {
		var cmd tea.Cmd
		m.textInput, cmd = m.textInput.Update(msg)
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

	case "enter":
		// Accept autocomplete suggestion before submitting
		if suggestion := m.textInput.CurrentSuggestion(); suggestion != "" {
			m.textInput.SetValue(suggestion)
			m.textInput.CursorEnd()
		}

		text := strings.TrimSpace(m.textInput.Value())
		if text == "" {
			return m, nil
		}
		m.textInput.SetValue("")
		m.completions = nil
		m.textInput.SetSuggestions(nil)
		m.interruptCount = 0
		m.lastError = ""

		// Handle slash commands locally or delegate
		if strings.HasPrefix(text, "/") {
			return m.handleSlashCommand(text)
		}

		return m.sendChat(text)

	case "up":
		// History navigation
		prev := historyPrevious()
		if prev != "" {
			m.textInput.SetValue(prev)
			m.textInput.CursorEnd()
		}
		return m, nil

	case "down":
		next := historyNext()
		m.textInput.SetValue(next)
		m.textInput.CursorEnd()
		return m, nil

	default:
		var cmd tea.Cmd
		m.textInput, cmd = m.textInput.Update(msg)
		m.updateCompletions()
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
		text := strings.TrimSpace(m.textInput.Value())
		if text != "" && len(m.messageQueue) < m.queueMax {
			m.messageQueue = append(m.messageQueue, text)
			m.textInput.SetValue("")
		}
		return m, nil

	default:
		// Allow typing while streaming
		var cmd tea.Cmd
		m.textInput, cmd = m.textInput.Update(msg)
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
	m.statusBar.Layer = ""

	// Send to backend — keep textInput focused for parallel typing
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

	// Update layer indicator
	switch msg.LayerUsed {
	case 1:
		m.statusBar.Layer = "[L1]"
	case 2:
		m.statusBar.Layer = "[L2]"
	case 3:
		m.statusBar.Layer = "[L3]"
	case 4:
		m.statusBar.Layer = "[L4]"
	default:
		m.statusBar.Layer = ""
	}

	// Build scrollback output
	var cmds []tea.Cmd

	// Tool calls summary
	for _, tc := range m.toolCalls {
		icon := toolIcon(tc.Status)
		line := icon + " " + toolCallStyle.Render(tc.Name)
		if tc.Result != "" {
			result := tc.Result
			if len(result) > 200 {
				result = result[:197] + "..."
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
	m.textInput.Focus()

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
			return m, tea.Println(errorStyle.Render("Backend not connected — /resume requires the Python backend"))
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
		return m, tea.Println(errorStyle.Render("Backend not connected — " + text + " requires the Python backend"))
	}
}

// updateToolCall updates or appends a tool call entry.
func (m *model) updateToolCall(msg backendToolCallMsg) {
	// Update existing entry if found
	for i := range m.toolCalls {
		if m.toolCalls[i].Name == msg.Name && m.toolCalls[i].Status == "running" {
			m.toolCalls[i].Status = msg.Status
			m.toolCalls[i].Result = msg.Result
			// Track edits
			if msg.Status == "completed" && msg.Name == "write_file" {
				m.statusBar.Edits++
			}
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
	text := m.textInput.Value()
	completions := getCompletions(text)
	if len(completions) > 0 {
		m.completions = completions
		m.textInput.SetSuggestions(completions)
	} else {
		m.completions = nil
		m.textInput.SetSuggestions(nil)
	}
}
