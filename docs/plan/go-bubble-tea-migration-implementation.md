# Go Bubble Tea TUI Migration — Implementation Plan

## Context

HybridCoder's Python inline REPL (prompt_toolkit + patch_stdout) hit 3 fundamental limitations: line-buffered token streaming, unsafe nested Applications (breaking arrow-key approvals), and no true fixed input areas. After extensive research across 3 deep-research documents, 7 additional research files, and 155 agent conversation entries, all agents (Claude, Codex, OpenCode) approved migrating to a **Go Bubble Tea frontend + Python backend** architecture. This plan synthesizes the research into an opinionated, executable implementation plan.

---

## Recommended Approach: Go Bubble Tea v1.3.10 + Python Backend via JSON-RPC

### Why v1, not v2
- v2 is still RC (>1 year in pre-release). Bubbles/Lip Gloss/Glamour/Huh do NOT have v2-compatible stable releases yet.
- v1.3.10 is battle-tested (OpenCode, lazygit, Soft Serve). Inline mode + `tea.Println()` + line-by-line diff renderer work.
- Migration to v2 is mechanical (View() returns `tea.View` instead of `string`, key messages split). Do it when v2 ships stable.

### Why custom JSON-RPC (not sourcegraph/jsonrpc2)
- Protocol is asymmetric: Go sends requests, Python sends notifications.
- ~100 lines of custom code vs adding a dependency designed for bidirectional LSP-style RPC.
- Wire format is identical JSON-RPC 2.0 — switching to a library later is trivial.

### Why no Huh for approvals
- Approvals are always 3 items. A 30-line custom selector beats importing a form framework.
- All agents verified simple selector is the right call.

---

## Dependency Versions

```
github.com/charmbracelet/bubbletea  v1.3.10
github.com/charmbracelet/bubbles    v0.20.0
github.com/charmbracelet/lipgloss   v1.0.0
github.com/charmbracelet/glamour    v0.8.0
github.com/sahilm/fuzzy             v0.1.1
golang.org/x/term                   v0.27.0
```

**Not included**: `huh` (overkill for 3 items), `sourcegraph/jsonrpc2` (overkill for asymmetric protocol), any SQLite driver (Python owns persistence), `knz/bubbline` (standard textinput + custom history sufficient).

---

## 8 Architectural Decisions That Prevent a Rewrite

| # | Decision | Implementation |
|---|----------|---------------|
| 1 | **No viewport for history** — O(1) View() | `tea.Println()` commits to scrollback. Live area = current response + input + status only. Do NOT import `bubbles/viewport`. |
| 2 | **Token batching at 16ms** | `strings.Builder` accumulates chunks. `tea.Tick(16ms)` flushes to model. Bubble Tea's 60fps renderer coalesces. |
| 3 | **Context cancellation in every Cmd** | Backend reader goroutine receives `context.WithCancel`. Cancel on Esc/Ctrl+C. |
| 4 | **Windows resize polling (spike-gated)** | Only if Phase 0 spike proves Bubble Tea's built-in `tea.WindowSizeMsg` is missing/incorrect on Windows Terminal. If needed: build-tagged `backend_windows.go`, poll `term.GetSize()` at 4fps (not 30fps), emit synthetic `WindowSizeMsg`. If not needed: delete the decision. |
| 5 | **Non-TUI output mode** | Check `TERM=dumb` or `!isatty(stdout)` at startup. Linear stdout mode for CI/pipes/accessibility. |
| 6 | **Pure-Go dependencies (no CGo)** | Go binary has zero native deps. Python handles SQLite + tree-sitter + LLM inference. |
| 7 | **Process group cleanup** | Unix: `Setpgid + kill(-pid)`. Windows: Job Objects via `golang.org/x/sys/windows`. |
| 8 | **Ctrl+C state machine** | Streaming: cancel + clear queue. Idle: warn. Second press: quit. |

---

## Phased Implementation

### Phase 0: Windows Spike (1 day)

**Goal**: Validate 6 acceptance criteria before writing production code.

Build `cmd/spike/main.go` (~250 lines, deleted after validation):
1. Inline mode (no alt-screen) in main terminal buffer
2. Fixed input visible while simulated streaming
3. Enter during streaming queues FIFO
4. Arrow-key approval selector works (Up/Down/Enter)
5. Native scrollback preserved after exit
6. `tea.Println()` commits completed turns above live area
7. `tea.WindowSizeMsg` fires on terminal resize (determines if Decision #4 resize polling is needed)

**Gate**: If criteria 1-6 fail on Windows Terminal, stop and investigate. Criterion 7 informs Decision #4 (resize polling) — if it works, no polling needed.

### Phase 1: Foundation (3-4 days)

**Day 1**: Go module + JSON-RPC protocol
- `cmd/hybridcoder-tui/go.mod` — module definition
- `cmd/hybridcoder-tui/protocol.go` — JSON-RPC message types
- `cmd/hybridcoder-tui/backend.go` — Python subprocess management, 3 goroutines (main/reader/writer)

**Day 2**: Python backend adapter
- `src/hybridcoder/backend/server.py` — JSON-RPC wrapper around AgentLoop
- `src/hybridcoder/cli.py` — Add `hybridcoder serve` command

**Day 3-4**: Basic TUI shell
- `cmd/hybridcoder-tui/main.go` — Entry point, backend discovery, non-TUI mode check
- `cmd/hybridcoder-tui/model.go` — Root model struct
- `cmd/hybridcoder-tui/update.go` — Update function, message routing
- `cmd/hybridcoder-tui/view.go` — View rendering (O(1) layout)
- `cmd/hybridcoder-tui/styles.go` — Lip Gloss styles
- `cmd/hybridcoder-tui/statusbar.go` — Status bar component

**Deliverable**: Go TUI starts, launches Python backend, bidirectional JSON-RPC works, input bar shown.

### Phase 2: Core Features (4-5 days)

**Day 5**: Streaming display — token batching + plain text live area + `tea.Println()` commits (see Streaming Render Rule below)
**Day 6**: Arrow-key approval prompts (`approval.go`, `askuser.go`) — THE P0 win
**Day 7**: Cancel + message queue — Ctrl+C state machine, FIFO queue (max 10)
**Day 8**: Slash commands + thinking indicator — `/` prefix detection, `spinner.Model`
**Day 9**: End-to-end integration testing on Windows Terminal

**Deliverable**: Full chat loop: send message -> streaming response -> approve tools -> follow-up. Cancel works. Queue works.

### Phase 3: Polish (3-4 days)

**Day 10**: Glamour markdown rendering — sanitize partial markdown, reuse TermRenderer
**Day 11**: Autocomplete — ghost text (`SetSuggestions`), custom dropdown (above input, VS Code style), `sahilm/fuzzy`
**Day 12**: Command history + @file references — file-backed history, `@` trigger
**Day 13**: Terminal detection — tmux/ssh/dumb/WT_SESSION checks in `detect.go`

**Deliverable**: Production-quality UX with markdown, autocomplete, history, and terminal compatibility.

### Phase 4: Production Hardening (2-3 days)

**Day 14**: Resource management — pprof on `localhost:6060` in debug mode, bounded 100KB streaming buffer, `goleak` in tests
**Day 15**: Process management — `backend_unix.go` (process group kill), `backend_windows.go` (Job Objects), graceful shutdown, backend crash recovery
**Day 16**: CLI integration — Go TUI as default for `hybridcoder chat`, `--legacy` for Python inline, Makefile targets

**Deliverable**: Production-ready binary with hardened process management and resource limits.

---

## File Structure (Go)

```
cmd/hybridcoder-tui/
    go.mod, go.sum
    main.go              # Entry point, --debug, backend discovery, non-TUI check
    model.go             # Root model struct (stage, dimensions, config)
    update.go            # Update(): message routing, Ctrl+C state machine, resize
    view.go              # View(): O(1) layout (streaming + separator + input + status)
    backend.go           # BackendProcess: subprocess, stdin writer, stdout reader
    backend_unix.go      # Process group management (build-tagged)
    backend_windows.go   # Job Object management (build-tagged)
    protocol.go          # JSON-RPC types (Request, Notification, method constants)
    approval.go          # Arrow-key approval selector (30-line custom)
    askuser.go           # Ask-user prompt (options + free-text)
    commands.go          # Slash command detection (/exit, /clear local; rest delegated)
    statusbar.go         # Status bar (model/provider/mode/tokens/queue)
    styles.go            # Lip Gloss styles
    markdown.go          # Glamour wrapper + partial markdown sanitization
    completion.go        # Autocomplete dropdown + fuzzy matching
    history.go           # File-backed command history
    detect.go            # Terminal/multiplexer detection matrix
    messages.go          # All custom tea.Msg types (one file, exhaustive)
    *_test.go            # Tests
```

## File Structure (Python — new/modified)

```
src/hybridcoder/backend/
    __init__.py
    server.py            # JSON-RPC server wrapping AgentLoop (NEW)
src/hybridcoder/cli.py   # Add `hybridcoder serve` command (MODIFY)
```

---

## Top 5 Production Risks + Mitigations

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | **Windows pipe deadlock** — Go writes stdin while Python stdout buffer full | 3 goroutines always: main (Bubble Tea), reader (stdout), writer (buffered channel -> stdin) |
| 2 | **Orphaned processes** — Go crash leaves Python + shell commands running | Unix: Setpgid + kill(-pid). Windows: Job Objects. Deferred cleanup in main(). |
| 3 | **tmux freeze** — AdaptiveColor queries hang on tmux <3.4 | Detect `$TMUX` at startup, disable adaptive colors, force ANSI256 profile |
| 4 | **Streaming memory growth** — 5000-line LLM response bloats live area | Cap `currentContent` at 100KB displayed. Show last 50 lines + "[XX lines above]". Full content in scrollback. |
| 5 | **Backend discovery on Windows** — `hybridcoder` not on PATH | Ordered discovery: `$HYBRIDCODER_BACKEND` -> PATH -> `uv run` -> `python -m` -> clear error |

---

## What Stays in Python vs Moves to Go

**Stays in Python (unchanged)**: agent loop, 6 tools, approval manager, 2 LLM providers, session store, config, 14 command handlers, inline REPL (as `--legacy`), Textual TUI (as `--tui`).

**New Python** (thin adapter): `backend/server.py` — JSON-RPC wrapper around existing callbacks.

**Go frontend**: Input handling, rendering, streaming display, approval UI (arrow-keys), ask-user UI, status bar, autocomplete, terminal detection, process management.

**Boundary**: Go owns everything the user sees and types. Python owns everything the LLM does and all persistent state.

---

## Build / Packaging / Discovery

### Binary Location

The Go binary lives at `cmd/hybridcoder-tui/` and builds to a single executable (`hybridcoder-tui` / `hybridcoder-tui.exe`).

| Context | Binary Location |
|---------|----------------|
| Dev (local build) | `cmd/hybridcoder-tui/hybridcoder-tui(.exe)` via `go build` |
| Dev (Makefile) | `build/hybridcoder-tui(.exe)` via `make tui` |
| Release | Pre-built binary bundled alongside Python package (or downloaded on first run) |

### How `hybridcoder chat` chooses Go vs `--legacy`

```
hybridcoder chat           -> Try Go TUI first, fall back to Python inline
hybridcoder chat --legacy  -> Force Python inline REPL (prompt_toolkit)
hybridcoder chat --tui     -> Force Textual TUI (existing)
```

Discovery order for the Go binary (in `src/hybridcoder/cli.py`):
1. `$HYBRIDCODER_TUI_BIN` env var (explicit override)
2. `build/hybridcoder-tui(.exe)` relative to project root (dev builds)
3. `hybridcoder-tui` on `$PATH` (installed release)
4. Fall back to `--legacy` with a one-time warning: "Go TUI not found, using legacy mode. Build with `make tui` or set $HYBRIDCODER_TUI_BIN."

### When Go isn't installed

Go is only needed to **build** the TUI, not to run it (it's a static binary). If the binary doesn't exist and Go isn't installed, the user gets the fallback warning above. No hard dependency on Go at runtime.

### Versioning

The Go binary embeds its version via `go build -ldflags "-X main.version=..."`. The Python backend checks `hybridcoder-tui --version` at startup and warns if there's a major version mismatch with the Python package version.

---

## JSON-RPC Protocol Spec

### Wire Format

- Transport: stdin/stdout pipes (no HTTP, no LSP Content-Length headers)
- Encoding: JSON-RPC 2.0, one JSON object per line (newline-delimited)
- Direction: **asymmetric** — Go sends requests, Python sends responses + unsolicited notifications

### Message Types

| Direction | Type | Example |
|-----------|------|---------|
| Go -> Python | Request | `{"jsonrpc":"2.0","id":1,"method":"submit","params":{"text":"fix the bug"}}` |
| Python -> Go | Response | `{"jsonrpc":"2.0","id":1,"result":{"status":"accepted"}}` |
| Python -> Go | Notification | `{"jsonrpc":"2.0","method":"on_token","params":{"text":"Hello"}}` |
| Go -> Python | Notification | `{"jsonrpc":"2.0","method":"cancel","params":{}}` |

### Request/Response Correlation

- Go assigns monotonically increasing integer IDs starting at 1.
- Go maintains a `map[int]chan<- json.RawMessage` for pending requests.
- Reader goroutine: if message has `id` field, route to pending map; if no `id`, route as notification.
- Timeout: 30s default per request. On timeout, remove from pending map and surface error to UI.

### Notification Handling

Python -> Go notifications (no `id` field) are dispatched by `method` name:
- `on_token` — streaming token chunk
- `on_done` — response complete
- `on_thinking` — thinking token
- `on_tool_request` — approval prompt
- `on_ask_user` — ask-user prompt
- `on_status` — status bar update
- `on_error` — error display

### Cancel Semantics

- Go sends `{"jsonrpc":"2.0","method":"cancel","params":{}}` (notification, no `id`).
- Python: cancels current operation, flushes any pending output, sends `on_done` with `cancelled: true`.
- Go: on receiving `on_done` with `cancelled: true`, clears live area and dequeues next message (if any).

### Shutdown

Orderly: Go sends `{"jsonrpc":"2.0","id":N,"method":"shutdown","params":{}}`. Python responds with `{"jsonrpc":"2.0","id":N,"result":{}}` then exits. Go waits up to 5s for process exit, then kills.

Abrupt: Go closes stdin pipe. Python detects EOF on stdin and exits. Go kills process group after 2s grace period.

### Backpressure

- Go -> Python: Writer goroutine pulls from a buffered channel (cap 64). If channel full, oldest message dropped with warning logged.
- Python -> Go: Reader goroutine reads continuously. If Go's Update loop can't keep up, token messages accumulate in the channel buffer (cap 256). At capacity, reader blocks (Python's stdout buffer fills, Python blocks on write — acceptable since it means Go is overwhelmed and Python should slow down).

### Transport Tests (Phase 1, Day 1)

1. **Golden encode/decode** — round-trip all message types through `json.Marshal` / `json.Decoder`
2. **Request/response correlation** — send 10 concurrent requests, verify each gets the correct response
3. **Notification flood** — send 1000 notifications in rapid succession, verify none lost
4. **Timeout** — send request with no response, verify timeout fires and pending map is cleaned
5. **Shutdown** — verify orderly shutdown sequence completes within 5s
6. **EOF handling** — close stdin, verify reader goroutine exits cleanly

---

## Streaming Render Rule

**During streaming** (tokens arriving): Render **plain text only** in the live area. No Glamour/markdown processing. This avoids:
- Glamour re-rendering cost per tick (16ms budget)
- Flickering from partial markdown (unclosed fences, incomplete tables)
- Memory allocation churn from TermRenderer

**On completion** (`on_done` received): Render the full response through Glamour **once**, then commit the rendered result to scrollback via `tea.Println()` and clear the live area.

**Exception**: If a future requirement demands partial markdown rendering mid-stream (e.g., rendering completed code blocks while still streaming), rate-limit Glamour calls to at most once per 500ms, accept degraded formatting for incomplete blocks, and mark this as a Phase 3 polish item.

---

## Verification Checklist

| # | Criterion | How |
|---|-----------|-----|
| 1 | Go TUI builds | `go build ./cmd/hybridcoder-tui/` |
| 2 | Backend starts | Go TUI launches Python subprocess successfully |
| 3 | Streaming works | Send message, see tokens stream, response commits to scrollback |
| 4 | Input stays fixed | Input bar doesn't move during streaming |
| 5 | Arrow-key selects | Approval prompt: cursor with Up/Down/Enter |
| 6 | Cancel works | Esc/Ctrl+C cancels generation + clears queue |
| 7 | Message queue | Submit during generation -> runs after completion |
| 8 | Windows works | No ANSI corruption on Windows Terminal |
| 9 | Python tests pass | `uv run pytest tests/ -v` (existing 509+ tests) |
| 10 | Markdown renders | Glamour-formatted responses with syntax highlighting |
| 11 | Slash commands | `/help`, `/model`, `/mode` delegated to Python backend |
| 12 | tmux safe | No freeze when launched inside tmux |

---

## Timeline Summary

**Total estimated effort: ~16 working days** across 4 phases, starting with a 1-day Windows spike as a gate.
