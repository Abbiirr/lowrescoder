package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os/exec"
	"sync"
	"sync/atomic"
	"time"

	tea "github.com/charmbracelet/bubbletea"
)

// Backend manages the Python backend subprocess and JSON-RPC communication.
type Backend struct {
	cmd     *exec.Cmd
	stdin   io.WriteCloser
	stdout  io.ReadCloser
	stderr  io.ReadCloser
	program *tea.Program

	writeCh chan []byte
	nextID  atomic.Int64
	pending sync.Map // map[int]chan RPCMessage

	cancel context.CancelFunc
	wg     sync.WaitGroup
}

// NewBackend creates a new Backend instance.
func NewBackend() *Backend {
	return &Backend{
		writeCh: make(chan []byte, 64),
	}
}

// Start launches the Python backend subprocess and starts reader/writer goroutines.
func (b *Backend) Start(ctx context.Context, program *tea.Program, pythonCmd string, args []string) error {
	b.program = program

	ctx, cancel := context.WithCancel(ctx)
	b.cancel = cancel

	b.cmd = exec.CommandContext(ctx, pythonCmd, args...)
	setProcAttr(b.cmd)

	var err error
	b.stdin, err = b.cmd.StdinPipe()
	if err != nil {
		cancel()
		return fmt.Errorf("stdin pipe: %w", err)
	}
	b.stdout, err = b.cmd.StdoutPipe()
	if err != nil {
		cancel()
		return fmt.Errorf("stdout pipe: %w", err)
	}
	b.stderr, err = b.cmd.StderrPipe()
	if err != nil {
		cancel()
		return fmt.Errorf("stderr pipe: %w", err)
	}

	if err := b.cmd.Start(); err != nil {
		cancel()
		return fmt.Errorf("start backend: %w", err)
	}

	b.nextID.Store(1)

	b.wg.Add(3)
	go b.readLoop(ctx)
	go b.writeLoop(ctx)
	go b.drainStderr(ctx)

	return nil
}

// SendRequest sends a JSON-RPC request to the Python backend and returns the request ID.
func (b *Backend) SendRequest(method string, params interface{}) int {
	id := int(b.nextID.Add(1) - 1)
	req := RPCRequest{
		JSONRPC: "2.0",
		ID:      id,
		Method:  method,
		Params:  params,
	}
	data, err := json.Marshal(req)
	if err != nil {
		return -1
	}
	data = append(data, '\n')

	select {
	case b.writeCh <- data:
		return id
	default:
		// Best effort for control-path messages: avoid dropping cancel/shutdown.
		if method == "cancel" || method == "shutdown" {
			select {
			case b.writeCh <- data:
				return id
			case <-time.After(500 * time.Millisecond):
			}
		}
		if b.program != nil {
			b.program.Send(backendErrorMsg{Message: "backend write queue full; dropped request: " + method})
		}
		return -1
	}
}

// SendResponse sends a JSON-RPC response to the Python backend (for approval/ask_user answers).
func (b *Backend) SendResponse(id int, result interface{}) {
	resp := RPCResponse{
		JSONRPC: "2.0",
		ID:      id,
		Result:  result,
	}
	data, err := json.Marshal(resp)
	if err != nil {
		return
	}
	data = append(data, '\n')

	select {
	case b.writeCh <- data:
	default:
		// Approval/ask-user responses are control-path messages. Block briefly
		// before giving up so we don't strand the backend waiting for input.
		select {
		case b.writeCh <- data:
		case <-time.After(500 * time.Millisecond):
			if b.program != nil {
				b.program.Send(backendErrorMsg{Message: "backend write queue full; dropped response"})
			}
		}
	}
}

// Shutdown gracefully shuts down the backend.
func (b *Backend) Shutdown() {
	// Best-effort orderly shutdown.
	b.SendRequest("shutdown", struct{}{})

	exited := make(chan struct{})
	go func() {
		if b.cmd != nil {
			_ = b.cmd.Wait()
		}
		close(exited)
	}()

	select {
	case <-exited:
	case <-time.After(5 * time.Second):
		if b.cancel != nil {
			b.cancel()
		}
		if b.cmd != nil && b.cmd.Process != nil {
			killProcessGroup(b.cmd)
		}
		select {
		case <-exited:
		case <-time.After(1 * time.Second):
		}
	}

	if b.cancel != nil {
		b.cancel()
	}
	if b.stdin != nil {
		_ = b.stdin.Close()
	}

	done := make(chan struct{})
	go func() {
		b.wg.Wait()
		close(done)
	}()

	select {
	case <-done:
	case <-time.After(2 * time.Second):
	}
}

// readLoop reads JSON-RPC messages from the backend's stdout.
func (b *Backend) readLoop(ctx context.Context) {
	defer b.wg.Done()

	reader := bufio.NewReader(b.stdout)
	var exitErr error

	for {
		select {
		case <-ctx.Done():
			return
		default:
		}

		line, err := reader.ReadBytes('\n')
		if len(line) > 0 {
			line = bytes.TrimSpace(line)
			if len(line) > 0 {
				var msg RPCMessage
				if unmarshalErr := json.Unmarshal(line, &msg); unmarshalErr != nil {
					if b.program != nil {
						b.program.Send(backendErrorMsg{Message: "[backend] invalid JSON-RPC message dropped"})
					}
				} else {
					// Route message based on type
					if msg.ID != nil && msg.Method == "" {
						// Response to a request we sent
						b.routeResponse(msg)
					} else if msg.ID != nil && msg.Method != "" {
						// Request from Python (approval/ask_user)
						b.routeRequest(msg)
					} else if msg.Method != "" {
						// Notification
						b.dispatchNotification(msg)
					}
				}
			}
		}
		if err != nil {
			if errors.Is(err, io.EOF) {
				break
			}
			exitErr = err
			break
		}
	}

	// Backend process exited
	if b.program != nil {
		b.program.Send(backendExitMsg{Err: exitErr})
	}
}

// writeLoop sends queued messages to the backend's stdin.
func (b *Backend) writeLoop(ctx context.Context) {
	defer b.wg.Done()

	writer := bufio.NewWriter(b.stdin)

	for {
		select {
		case <-ctx.Done():
			return
		case data := <-b.writeCh:
			if _, err := writer.Write(data); err != nil {
				return
			}
			// Drain any additional pending writes
			drained := true
			for drained {
				select {
				case more := <-b.writeCh:
					if _, err := writer.Write(more); err != nil {
						return
					}
				default:
					drained = false
				}
			}
			if err := writer.Flush(); err != nil {
				return
			}
		}
	}
}

// drainStderr reads stderr output from the backend and surfaces errors to the TUI.
func (b *Backend) drainStderr(ctx context.Context) {
	defer b.wg.Done()

	scanner := bufio.NewScanner(b.stderr)
	scanner.Buffer(make([]byte, 0, 64*1024), 64*1024) // 64KB max line

	for scanner.Scan() {
		select {
		case <-ctx.Done():
			return
		default:
		}
		line := scanner.Text()
		if line == "" {
			continue
		}
		// Surface backend stderr as error messages
		if b.program != nil {
			b.program.Send(backendErrorMsg{Message: "[backend] " + line})
		}
	}
}

// SendRequestCmd sends a JSON-RPC request and returns a tea.Cmd that blocks until the
// response arrives, then calls the callback to produce a tea.Msg.
func (b *Backend) SendRequestCmd(method string, params interface{}, callback func(json.RawMessage, *RPCError) tea.Msg) tea.Cmd {
	id := int(b.nextID.Add(1) - 1)
	req := RPCRequest{
		JSONRPC: "2.0",
		ID:      id,
		Method:  method,
		Params:  params,
	}
	data, err := json.Marshal(req)
	if err != nil {
		return func() tea.Msg {
			return backendErrorMsg{Message: "failed to marshal request: " + err.Error()}
		}
	}
	data = append(data, '\n')

	// Register a pending channel BEFORE sending, so the response can't arrive first.
	ch := make(chan RPCMessage, 1)
	b.pending.Store(id, ch)

	select {
	case b.writeCh <- data:
	default:
		b.pending.Delete(id)
		return func() tea.Msg {
			return backendErrorMsg{Message: "backend write channel full"}
		}
	}

	return func() tea.Msg {
		select {
		case resp := <-ch:
			if resp.Error != nil {
				return callback(nil, resp.Error)
			}
			return callback(resp.Result, nil)
		case <-time.After(30 * time.Second):
			b.pending.Delete(id)
			return backendErrorMsg{Message: method + " timed out waiting for backend response"}
		}
	}
}

// routeResponse routes a JSON-RPC response to a pending request's channel.
func (b *Backend) routeResponse(msg RPCMessage) {
	if msg.ID == nil {
		return
	}
	if ch, ok := b.pending.LoadAndDelete(*msg.ID); ok {
		ch.(chan RPCMessage) <- msg
	}
}

// routeRequest handles a request from Python (approval/ask_user).
func (b *Backend) routeRequest(msg RPCMessage) {
	if msg.ID == nil || b.program == nil {
		return
	}

	switch msg.Method {
	case "on_tool_request":
		var params ApprovalRequestParams
		if err := json.Unmarshal(msg.Params, &params); err != nil {
			return
		}
		b.program.Send(backendApprovalRequestMsg{
			RequestID: *msg.ID,
			Tool:      params.Tool,
			Args:      params.Args,
		})

	case "on_ask_user":
		var params AskUserRequestParams
		if err := json.Unmarshal(msg.Params, &params); err != nil {
			return
		}
		b.program.Send(backendAskUserRequestMsg{
			RequestID: *msg.ID,
			Question:  params.Question,
			Options:   params.Options,
			AllowText: params.AllowText,
		})
	}
}

// dispatchNotification converts a notification into a tea.Msg and sends it to the program.
func (b *Backend) dispatchNotification(msg RPCMessage) {
	if b.program == nil {
		return
	}

	switch msg.Method {
	case "on_token":
		var params TokenParams
		if err := json.Unmarshal(msg.Params, &params); err != nil {
			return
		}
		b.program.Send(backendTokenMsg{Text: params.Text})

	case "on_thinking":
		var params ThinkingParams
		if err := json.Unmarshal(msg.Params, &params); err != nil {
			return
		}
		b.program.Send(backendThinkingMsg{Text: params.Text})

	case "on_tool_call":
		var params ToolCallParams
		if err := json.Unmarshal(msg.Params, &params); err != nil {
			return
		}
		b.program.Send(backendToolCallMsg{
			Name:   params.Name,
			Status: params.Status,
			Result: params.Result,
			Args:   params.Args,
		})

	case "on_done":
		var params DoneParams
		if err := json.Unmarshal(msg.Params, &params); err != nil {
			return
		}
		b.program.Send(backendDoneMsg{
			TokensIn:  params.TokensIn,
			TokensOut: params.TokensOut,
			Cancelled: params.Cancelled,
			LayerUsed: params.LayerUsed,
		})

	case "on_error":
		var params ErrorParams
		if err := json.Unmarshal(msg.Params, &params); err != nil {
			return
		}
		b.program.Send(backendErrorMsg{Message: params.Message})

	case "on_status":
		var params StatusParams
		if err := json.Unmarshal(msg.Params, &params); err != nil {
			return
		}
		b.program.Send(backendStatusMsg{
			Model:     params.Model,
			Provider:  params.Provider,
			Mode:      params.Mode,
			SessionID: params.SessionID,
		})
	}
}
