# Go Bubble Tea TUI Migration Plan

> Detailed architecture design and migration plan for replacing the Python inline REPL with a Go Bubble Tea frontend.
> Last updated: 2026-02-07

---

## 1. Why This Migration

### Problem Summary

The Python inline REPL (`prompt_toolkit` + `patch_stdout(raw=True)`) has three fundamental limitations:

1. **`patch_stdout` is line-buffered** — Token streaming interleaves with the prompt (e.g., `Hello> who a` bug). This is inherent to how `StdoutProxy` works and cannot be fully fixed with separators or throttling (see Codex Entry 137).

2. **Nested prompt_toolkit Applications are unsafe** — Arrow-key selects (`_arrow_select()`) can't coexist with an active `PromptSession`. This forced a UX downgrade to typed `y/s/n` responses in parallel mode.

3. **No true fixed areas** — `patch_stdout` simulates a bottom-pinned prompt but flickers during streaming. There's no clean visual boundary between output and input.

### How Claude Code Actually Renders

Based on research of Claude Code internals:

- Uses React + Ink with a **custom differential renderer**
- **Cursor-up-and-redraw** technique (NOT ANSI scroll regions, NOT alternate screen)
- `<Static>` component makes completed messages permanent scrollback
- Only the "live area" (current response + input) gets redrawn per frame
- **Synchronized Output (DEC 2026)** optionally prevents flicker (feature-detected, not required)
- Boris Cherny (Anthropic) called Ink "amazing but sort of hacky and janky"
- Codex CLI **rewrote from Ink to Rust + Ratatui** for performance

### Why Go Bubble Tea Wins

| Factor | Assessment |
|--------|-----------|
| Architecture | Elm Architecture (Model-Update-View) — clean state management |
| Inline rendering | Supported without alternate screen — preserves terminal scrollback |
| Concurrency | Goroutines make concurrent streaming + input trivial |
| Distribution | Single binary (~10-15MB), zero runtime dependencies |
| Cross-platform | Windows 10+ support (fixed flickering in v0.26+) |
| Proven in production | OpenCode (Go-based AI coding agent built on Bubble Tea) |
| Ecosystem | Lip Gloss (styling), Glamour (Markdown), Huh (forms), Bubbles (components) |

---

## 2. High-Level Architecture

```
+---------------------------------------------+
|           Go Binary (TUI Frontend)           |
|  Bubble Tea + Bubbles + Lip Gloss + Glamour  |
|                                              |
|  +--------------------------------------+   |
|  |  Live Area (current response only)    |   |
|  |  - Streaming tokens from LLM         |   |
|  |  - Tool call results (in progress)   |   |
|  |  - Thinking indicators               |   |
|  |  - Glamour-rendered Markdown          |   |
|  |  (completed turns committed to        |   |
|  |   native scrollback via tea.Println)  |   |
|  +--------------------------------------+   |
|  |  ----------- (separator) ----------- |   |
|  +--------------------------------------+   |
|  |  TextInput (fixed input bar)          |   |
|  |  - Command history + completion       |   |
|  |  - Arrow-key suggestion navigation    |   |
|  +--------------------------------------+   |
|  |  StatusBar (model/mode/tokens/queue)  |   |
|  +--------------------------------------+   |
|                    |                         |
|          JSON-RPC over stdin/stdout          |
|                    |                         |
+--------------------+------------------------+
                     |
+--------------------+------------------------+
|           Python Process (Backend)           |
|                                              |
|  Agent Loop --- Tool Registry                |
|       |              |                       |
|  LLM Provider   Approval Manager             |
|  (Ollama/OR)         |                       |
|       |         Session Store (SQLite)        |
|  Streaming ---> stdout JSON-RPC              |
+---------------------------------------------+
```

### Key Insight

The Go TUI is the **frontend only**. Most existing Python code (agent loop, tools, LLM providers, session store) stays unchanged. We add a thin JSON-RPC adapter on the Python side.

### Scrollback Architecture

Completed conversation turns are committed to **native terminal scrollback** via `tea.Println()`. This means:
- Past messages are NOT managed by Bubble Tea — they are permanent terminal output
- Users can scroll up with native terminal scroll (mouse wheel, Shift+PgUp)
- Terminal text selection, search, and copy work naturally
- Bubble Tea's "live area" only contains: current streaming response + input bar + status bar
- This matches Claude Code's `<Static>` pattern in Ink

---

## 3. Communication Protocol: JSON-RPC over stdin/stdout

The Go TUI launches the Python backend as a subprocess. Communication uses newline-delimited JSON-RPC 2.0.

### Go -> Python (requests)

```json
{"jsonrpc":"2.0","method":"chat","params":{"message":"hello","session_id":"abc"},"id":1}
{"jsonrpc":"2.0","method":"approve_tool","params":{"approved":true,"session_approve":false},"id":2}
{"jsonrpc":"2.0","method":"answer_question","params":{"answer":"option1"},"id":3}
{"jsonrpc":"2.0","method":"cancel","params":{},"id":4}
{"jsonrpc":"2.0","method":"command","params":{"cmd":"/model qwen3:8b"},"id":5}
{"jsonrpc":"2.0","method":"session.new","params":{"title":"New session"},"id":6}
{"jsonrpc":"2.0","method":"session.resume","params":{"session_id":"abc123"},"id":7}
{"jsonrpc":"2.0","method":"session.list","params":{},"id":8}
{"jsonrpc":"2.0","method":"config.get","params":{},"id":9}
{"jsonrpc":"2.0","method":"config.set","params":{"key":"llm.model","value":"qwen3:8b"},"id":10}
```

### Python -> Go (streaming events / notifications)

```json
{"jsonrpc":"2.0","method":"on_chunk","params":{"text":"Hello"}}
{"jsonrpc":"2.0","method":"on_thinking","params":{"text":"Let me think..."}}
{"jsonrpc":"2.0","method":"on_tool_call","params":{"name":"write_file","status":"pending","args":{"path":"foo.py"}}}
{"jsonrpc":"2.0","method":"on_tool_result","params":{"name":"write_file","status":"completed","result":"Written to foo.py"}}
{"jsonrpc":"2.0","method":"on_approval_needed","params":{"tool":"write_file","args":{"path":"foo.py","content":"..."}}}
{"jsonrpc":"2.0","method":"on_ask_user","params":{"question":"Which?","options":["A","B"],"allow_text":true}}
{"jsonrpc":"2.0","method":"on_done","params":{"tokens_in":100,"tokens_out":200}}
{"jsonrpc":"2.0","method":"on_error","params":{"message":"Connection failed"}}
{"jsonrpc":"2.0","method":"on_status","params":{"model":"qwen3:8b","provider":"ollama","mode":"suggest"}}
```

### Protocol Notes

- Newline-delimited (each message is one line of JSON)
- Similar to LSP (Language Server Protocol) — language-agnostic
- Notifications (no `id`) are fire-and-forget events from backend to frontend
- Requests (with `id`) expect a response
- Backend sends `on_chunk` events as tokens stream — frontend appends to live area (committed to scrollback on completion)
- Use `json.Decoder` (not `bufio.Scanner`) for reading — no token size limits, handles unbounded payloads
- **Windows pipe deadlock prevention**: Use separate goroutines for reading stdout and writing stdin. Windows named pipes have a 4KB buffer — a blocked write can deadlock if the reader isn't draining. Always: one goroutine reads stdout, another writes stdin, main goroutine runs Bubble Tea

---

## 4. Go TUI Components (Bubble Tea)

### 4.1 Root Model

```go
type stage int

const (
    stageInput    stage = iota // Ready for user input
    stageStreaming             // LLM is generating
    stageApproval              // Waiting for tool approval
    stageAskUser               // Waiting for user answer
)

type model struct {
    // NOTE: No viewport for past messages — completed turns go to native scrollback
    // via tea.Println(). Only the current streaming response is in the live area.
    textInput   textinput.Model   // Fixed input bar
    statusBar   statusBarModel    // Bottom status line
    spinner     spinner.Model     // Thinking indicator

    stage       stage             // Current interaction stage
    backend     *BackendProcess   // Python subprocess manager

    // Streaming state
    currentChunk strings.Builder  // Accumulates current response
    thinkingText string           // Current thinking content

    // Approval state
    approvalOptions []string
    approvalCursor  int
    approvalTool    string
    approvalArgs    map[string]interface{}

    // Ask-user state
    askQuestion    string
    askOptions     []string
    askCursor      int
    askAllowText   bool

    // Message queue
    messageQueue []string
    queueMax     int

    // Config
    width  int
    height int
}
```

### 4.2 View Layout

The live area rendered by Bubble Tea is intentionally minimal — only the current streaming response, input, and status. Completed turns are already in native scrollback above.

```go
func (m model) View() string {
    var sections []string

    // Current streaming response (only during active generation)
    if m.stage == stageStreaming && m.currentChunk.Len() > 0 {
        sections = append(sections, m.renderStreamingResponse())
    }

    // Separator
    separator := lipgloss.NewStyle().
        Foreground(lipgloss.Color("240")).
        Render(strings.Repeat("─", m.width))
    sections = append(sections, separator)

    // Input area (changes based on stage)
    switch m.stage {
    case stageApproval:
        sections = append(sections, m.renderApproval())
    case stageAskUser:
        sections = append(sections, m.renderAskUser())
    default:
        sections = append(sections, m.textInput.View())
    }

    // Status bar
    sections = append(sections, m.renderStatusBar())

    return lipgloss.JoinVertical(lipgloss.Top, sections...)
}

// When a response completes, commit it to native scrollback:
// tea.Println(renderedResponse)
// This makes it permanent terminal output — Bubble Tea no longer manages it.
```

### 4.3 Backend Communication (Goroutine)

```go
// Backend reader goroutine -- reads JSON-RPC from Python stdout
// Uses json.Decoder instead of bufio.Scanner for robustness:
// - No token size limits (Scanner has a max buffer)
// - Handles unbounded JSON payloads (large tool results)
// - More idiomatic for streaming JSON
func listenToBackend(p *tea.Program, stdout io.Reader) {
    decoder := json.NewDecoder(stdout)

    for decoder.More() {
        var msg jsonrpc.Message
        if err := decoder.Decode(&msg); err != nil {
            continue // Skip malformed messages
        }
        p.Send(backendMsg(msg)) // Thread-safe message injection
    }
}
```

### 4.4 Arrow-Key Approval Prompt

When the backend sends `on_approval_needed`, the TUI switches stage:

```go
case "on_approval_needed":
    m.stage = stageApproval
    m.approvalOptions = []string{
        "Yes",
        "Yes, this session",
        "No",
    }
    m.approvalCursor = 0
    m.approvalTool = params.Tool
    m.approvalArgs = params.Args
```

The approval view renders with arrow-key navigation:

```go
func (m model) renderApproval() string {
    var b strings.Builder
    b.WriteString("Allow " + m.approvalTool + "?\n")
    for i, opt := range m.approvalOptions {
        if i == m.approvalCursor {
            b.WriteString("  > " + opt + "\n")
        } else {
            b.WriteString("    " + opt + "\n")
        }
    }
    return b.String()
}
```

Up/Down keys move cursor, Enter selects, Escape cancels. This is just a stage change in the Elm model — no nested applications needed.

### 4.5 Cancel and Queue Semantics

- **Escape / Ctrl+C during streaming**: Cancels the current generation AND clears the message queue
- **Escape / Ctrl+C at idle prompt**: First press does nothing (prevents accidents); second press exits
- **Enter during streaming**: Message is queued (FIFO, max 10). Queued messages run sequentially after current completes
- **Queue indicator**: Status bar shows queue count when > 0 (e.g., `[queue: 2]`)

```go
case tea.KeyEscape, tea.KeyCtrlC:
    if m.stage == stageStreaming {
        m.messageQueue = nil  // Clear queue
        m.backend.Send("cancel", nil)
        m.stage = stageInput
    }
```

### 4.6 Slash Command Delegation

Most slash commands are **delegated to the Python backend** for parity with the existing `CommandRouter`:

| Handled in Go (local) | Delegated to Python |
|------------------------|-------------------|
| `/exit` (quit Go process) | `/model`, `/mode`, `/shell` (config changes) |
| Input history navigation | `/new`, `/sessions`, `/resume` (session management) |
| UI toggles (`/freeze`, `/thinking`) | `/compact` (session store operation) |
| `/clear` (terminal clear) | `/help` (command list from router) |
| | `/init`, `/copy` |

This ensures command behavior matches exactly without reimplementing logic in Go.

### 4.7 Feature Priority Matrix

| Feature | Bubble Tea Component | Priority |
|---------|---------------------|----------|
| Fixed input bar | `textinput.Model` | P0 |
| Native scrollback + live area | `tea.Println()` + inline renderer | P0 |
| Separator line | Lip Gloss styled string | P0 |
| Status bar | Custom model | P0 |
| Streaming tokens | `p.Send()` from goroutine | P0 |
| Arrow-key approvals | Stage switch + cursor rendering | P0 |
| Cancel (Esc/Ctrl+C) | Key binding -> backend cancel | P0 |
| Thinking indicator | `spinner.Model` | P1 |
| Slash commands | Input prefix detection | P1 |
| Command completion | `textinput.SetSuggestions()` | P1 |
| Message queue | `[]string` in model | P1 |
| Glamour Markdown | `glamour.Render()` for output | P1 |
| @file references | Custom completer | P2 |
| Session resume | Backend `--session` flag | P2 |
| Command history | File-backed history | P2 |

---

## 5. Python Backend Changes

### 5.1 New File: `src/hybridcoder/backend/server.py`

A thin JSON-RPC server that wraps the existing agent loop:

```python
"""JSON-RPC server that wraps the existing agent loop.

Reads requests from stdin, writes events to stdout.
Launched as a subprocess by the Go TUI.
"""
import asyncio
import json
import sys
from typing import Any

from hybridcoder.agent.loop import AgentLoop
from hybridcoder.agent.tools import create_default_registry
from hybridcoder.agent.approval import ApprovalManager, ApprovalMode
from hybridcoder.config import load_config
from hybridcoder.layer4.llm import create_provider
from hybridcoder.session.store import SessionStore


class BackendServer:
    def __init__(self):
        self.config = load_config()
        # ... initialize components (reuse existing classes)

    def emit(self, method: str, params: dict[str, Any]) -> None:
        """Send a JSON-RPC notification to stdout (Go TUI reads this)."""
        msg = {"jsonrpc": "2.0", "method": method, "params": params}
        sys.stdout.write(json.dumps(msg) + "\n")
        sys.stdout.flush()

    async def handle_chat(self, message: str, session_id: str) -> None:
        """Run agent loop with streaming callbacks that emit JSON-RPC."""
        agent_loop = self._ensure_agent_loop(session_id)
        await agent_loop.run(
            message,
            on_chunk=lambda text: self.emit("on_chunk", {"text": text}),
            on_thinking_chunk=lambda text: self.emit("on_thinking", {"text": text}),
            on_tool_call=lambda name, status, result: self.emit(
                "on_tool_call", {"name": name, "status": status, "result": result}
            ),
            approval_callback=self._approval_callback,
            ask_user_callback=self._ask_user_callback,
        )
        self.emit("on_done", {"tokens_in": 0, "tokens_out": 0})

    async def _approval_callback(self, tool_name: str, args: dict) -> bool:
        """Emit approval request, wait for Go TUI response."""
        self.emit("on_approval_needed", {"tool": tool_name, "args": args})
        # Wait for approve_tool request from Go TUI
        response = await self._wait_for_method("approve_tool")
        return response.get("approved", False)

    async def _ask_user_callback(self, question, options, allow_text) -> str:
        """Emit ask_user request, wait for Go TUI response."""
        self.emit("on_ask_user", {
            "question": question,
            "options": options,
            "allow_text": allow_text,
        })
        response = await self._wait_for_method("answer_question")
        return response.get("answer", "")
```

### 5.2 Existing Code Unchanged

The key insight: **most of the existing Python code stays unchanged:**

| Component | Changes Needed |
|-----------|---------------|
| `agent/loop.py` | None — callbacks already support streaming |
| `agent/tools.py` | None — tool registry unchanged |
| `agent/approval.py` | None — approval logic unchanged |
| `agent/prompts.py` | None — prompt building unchanged |
| `layer4/llm.py` | None — providers unchanged |
| `session/store.py` | None — SQLite store unchanged |
| `config.py` | None — config unchanged |
| `cli.py` | Minor: add `hybridcoder serve` command to launch backend mode |
| `inline/app.py` | None — stays as `--legacy` fallback |

### 5.3 Python Path Discovery

The Go binary needs to find and launch the Python backend. Strategy:

1. Look for `hybridcoder` on `PATH` (installed via `uv tool install` or `pip install`)
2. Fallback: look for `uv run hybridcoder serve` in the project directory
3. The Go binary embeds the expected backend protocol version and validates on handshake

---

## 6. File Structure (New Go Code)

```
cmd/
  hybridcoder-tui/
    main.go          # Entry point, launch backend subprocess
    model.go         # Root Bubble Tea model (state)
    view.go          # View rendering (layout, styles)
    update.go        # Message handling (Update function)
    backend.go       # Python subprocess management + JSON-RPC
    approval.go      # Arrow-key approval prompt logic
    askuser.go       # Ask-user prompt logic
    commands.go      # Slash command handling
    statusbar.go     # Status bar component
    styles.go        # Lip Gloss styles
    history.go       # Command history (file-backed)
go.mod
go.sum
```

---

## 7. Active-Frame Rendering Strategy

### The Claude Code Approach (What We're Replicating)

Claude Code renders in the **main terminal buffer** (no alternate screen) using a "cursor-up-and-redraw" technique:

1. **Completed messages** are printed as normal terminal output (become permanent scrollback)
2. **The "live area"** (current streaming response + input bar + status) is redrawn every frame
3. Each frame: move cursor up to the start of the live area, clear to end of screen, redraw
4. When response completes: "commit" the response text as permanent scrollback, reset live area

### Bubble Tea Implementation

Bubble Tea's `renderer` in inline mode already uses cursor-up-and-redraw:

```
Frame N:                    Frame N+1:
  [viewport content]          [viewport content]
  [---separator---]           [---separator---]
  [> input bar    ]           [> input bar    ]
  [status: model..]           [status: model..]

  ^-- cursor moves up         ^-- redraws from here
      to top of view              with new content
```

For "committing" completed content to scrollback:
- When a response completes, print the final rendered content as normal output (it becomes scrollback)
- Then start the next live area fresh below it

This matches how Bubble Tea's inline mode naturally works — the View() output is the "live area" that gets redrawn, and anything printed before it stays in scrollback.

### Synchronized Output (Optional Flicker Prevention)

DEC 2026 synchronized output is **optional** and **feature-detected**. It is NOT required for correctness — Bubble Tea's inline renderer works without it. When supported, it reduces flicker by telling the terminal to buffer and render atomically.

```go
// Feature detection: query terminal support via DECRQM before enabling
// Only enable if terminal confirms support (response: CSI ? 2026 ; 1 $ y)
if terminalSupportsDEC2026() {
    fmt.Print("\033[?2026h") // Begin synchronized update
    // ... render frame ...
    fmt.Print("\033[?2026l") // End synchronized update
}
```

**Support**: Windows Terminal, iTerm2, Alacritty, most modern terminals. NOT universally available — never assume it. Bubble Tea may handle this internally in future versions.

---

## 8. Windows-First Spike (1 Day, Before Full Implementation)

Before building the full Go TUI, validate the core assumptions with a minimal spike program on Windows Terminal. This was agreed upon in Entries 144, 148 (Codex), and 149 (Codex).

### Spike Acceptance Criteria

| # | Criterion | How to Verify |
|---|-----------|---------------|
| 1 | Inline mode (no alt-screen) | Program runs in main terminal buffer |
| 2 | Fixed input always visible while streaming | Type during streaming — keystrokes visible, no interleaving |
| 3 | Enter while streaming queues FIFO | Submit message during generation — appears after current completes |
| 4 | Approvals are arrow-select | Simulated approval prompt shows `❯` cursor with Up/Down/Enter |
| 5 | Native terminal scrollback | After Ctrl+C exit, scroll up to see full transcript in terminal history |
| 6 | `tea.Println()` commit pattern | Completed turns committed above live area, selectable with mouse |

### Spike Scope

Minimal Go program (~200 lines):
- Bubble Tea inline mode with `tea.WithoutSignalHandler()` and `tea.WithInput()`
- `textinput.Model` for input bar
- Simulated streaming (goroutine printing tokens via `p.Send()`)
- `tea.Println()` to commit completed messages to scrollback
- Simple arrow-key approval selector (stage switch pattern)

**Gate**: If spike fails any criterion on Windows Terminal, investigate root cause before proceeding. If unfixable, re-evaluate approach.

---

## 9. Migration Timeline

| Phase | What | Effort | Dependencies |
|-------|------|--------|-------------|
| **Week 1** | Set up Go module, deps (Bubble Tea, Lip Gloss, Glamour) | 1 day | None |
| **Week 1** | Build JSON-RPC protocol + Python backend adapter | 2 days | Go module |
| **Week 1-2** | Build Go TUI: viewport + input + separator + status bar | 3 days | JSON-RPC |
| **Week 2** | Add streaming display, thinking indicator | 2 days | TUI shell |
| **Week 2** | Add arrow-key approval prompts | 1 day | TUI shell |
| **Week 2-3** | Add slash commands, completion, message queue | 2 days | Approval |
| **Week 3** | Add Glamour Markdown rendering | 1 day | Streaming |
| **Week 3** | Testing, Windows verification, polish | 2 days | All above |
| **Week 3** | Switch default `hybridcoder chat` to use Go TUI | 1 day | All above |

**Total: ~3 weeks for a production-quality Go TUI.**

### Parallel Tracks

- Python inline mode (`--legacy` flag) remains as fallback — no changes needed
- Python backend server can be developed concurrently with Go TUI
- Existing Python tests continue to pass throughout migration

---

## 10. Verification Checklist

| # | Criterion | How to Verify |
|---|-----------|---------------|
| 1 | Go TUI builds | `go build ./cmd/hybridcoder-tui/` |
| 2 | Backend starts | Go TUI successfully launches Python subprocess |
| 3 | Streaming works | Type a message, see tokens stream in live area |
| 4 | Input stays fixed | Input bar doesn't move during streaming |
| 5 | Scrollback works | Scroll up through past messages in terminal |
| 6 | Arrow selects work | Approval prompt shows cursor with Up/Down/Enter |
| 7 | Cancel works | Escape/Ctrl+C cancels generation + clears queue |
| 8 | Message queue works | Submit during generation queues and runs after |
| 9 | Windows works | No ANSI corruption on Windows Terminal |
| 10 | Python tests pass | `uv run pytest tests/ -v` (existing tests unaffected) |
| 11 | Markdown renders | Assistant responses render with proper formatting |
| 12 | Slash commands work | `/help`, `/model`, `/mode`, etc. function correctly |

---

## 11. Go Dependencies

```
require (
    github.com/charmbracelet/bubbletea      v0.27+  // Core TUI framework
    github.com/charmbracelet/bubbles         v0.19+  // Component library
    github.com/charmbracelet/lipgloss        v0.13+  // Styling
    github.com/charmbracelet/glamour         v0.8+   // Markdown rendering
    github.com/charmbracelet/huh             v0.6+   // Forms (approvals, selects)
    github.com/sourcegraph/jsonrpc2          v0.2+   // JSON-RPC over stdio (battle-tested, used by Sourcegraph)
)
```

---

## 12. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Bubble Tea inline mode doesn't preserve scrollback | Low | High | OpenCode proves it works; test early |
| Windows Terminal rendering issues | Medium | Medium | Test on Windows early; Bubble Tea v0.26+ fixed flickering |
| JSON-RPC protocol complexity | Low | Medium | Keep protocol simple; add methods incrementally |
| Python subprocess management on Windows | Medium | Medium | Use `os/exec` with proper signal handling |
| Polyglot repo maintenance burden | Medium | Low | Clear separation: Go = UI, Python = logic |
| Glamour rendering limitations | Low | Low | Fallback to plain text if needed |
