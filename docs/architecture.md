# AutoCode Architecture

## Overview

AutoCode is a local-first AI coding assistant that runs on consumer hardware. It uses a **4-layer intelligence model** where classical AI techniques handle the majority of operations, invoking LLMs only when necessary.

The system is split into a **Rust TUI frontend** and a **Python backend**, communicating via JSON-RPC 2.0 over PTY stdin/stdout.

```
┌──────────────────────────────────────────┐
│         Rust TUI Frontend                │
│  (crossterm + ratatui + tokio,           │
│   inline mode by default)                │
│                                          │
│  Input ─ Streaming ─ Approvals           │
│  Autocomplete ─ History ─ Markdown       │
└──────────────┬───────────────────────────┘
               │ JSON-RPC 2.0
               │ (PTY stdin/stdout, newline-delimited)
┌──────────────┴───────────────────────────┐
│         Python Backend                   │
│  (autocode serve)                        │
│                                          │
│  Agent Loop ─ Tools ─ LLM Providers      │
│  Session Store ─ Config ─ Commands       │
└──────────────────────────────────────────┘
```

The Go BubbleTea TUI and the Python `--inline` fallback were the previous frontends; both were deleted at M11 cutover (2026-04-19). See `docs/decisions/ADR-001-rust-tui-migration.md` for the decision record.

---

## Frontend: Rust TUI

**Location:** `autocode/rtui/`
**Binary:** `autocode/rtui/target/release/autocode-tui` (~2.4 MB stripped)
**Stack:** `crossterm` 0.28 + `ratatui` 0.29 + `tokio` 1.x + `portable-pty` 0.8 + `serde_json` + `anyhow` + `tracing`

The Rust frontend handles all terminal interaction using ratatui (immediate-mode widgets over crossterm). It runs in **inline mode by default** (no alternate screen) to preserve native terminal scrollback; `--altscreen` opts into full-screen mode.

**Reference docs:** [`docs/reference/rust-tui-architecture.md`](reference/rust-tui-architecture.md) and [`docs/reference/rust-tui-rpc-contract.md`](reference/rust-tui-rpc-contract.md).

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Inline mode (no alt-screen) | Preserves native scrollback after exit |
| `tea.Println()` for completed turns | Commits content above the live area — O(1) View() |
| No viewport component | Scrollback is the terminal's job, not ours |
| 16ms token batching | Accumulate chunks in `strings.Builder`, flush on tick |
| Glamour markdown ONCE on done | Never render markdown during streaming (too expensive) |
| Custom 3-option approval selector | Simpler than importing a form framework for 3 items |

### File Structure

| File | Purpose |
|------|---------|
| `main.go` | Entry point: detect terminal, find Python backend, launch program |
| `model.go` | Root model struct, stage enum, `initialModel()` |
| `view.go` | O(1) View: live area only (streaming + tools + input + status) |
| `update.go` | Message routing, key handling, stage transitions |
| `backend.go` | Subprocess manager: 3 goroutines (reader/writer/stderr drain) |
| `backend_windows.go` | Windows process group management |
| `backend_unix.go` | Unix process group management (Setpgid + SIGKILL) |
| `protocol.go` | JSON-RPC 2.0 wire types (requests, responses, notifications) |
| `messages.go` | Custom `tea.Msg` types for all backend events |
| `styles.go` | Lip Gloss styles for all UI elements |
| `statusbar.go` | Status bar: model, provider, mode, tokens, queue |
| `approval.go` | Arrow-key tool approval selector (Yes/Yes session/No) |
| `askuser.go` | Ask-user prompt (options + free text) |
| `commands.go` | Slash command parsing and routing |
| `completion.go` | Prefix + fuzzy autocomplete via sahilm/fuzzy |
| `history.go` | Persistent command history (~/.autocode/go_history) |
| `markdown.go` | Glamour markdown rendering (called once per turn) |
| `detect.go` | Terminal detection (dumb term, isatty) + Python discovery |

### UI Stage Machine

```
stageInit ──(on_status)──► stageInput
                              │
                    (Enter)   │   (on_tool_request)
                              ▼
                        stageStreaming ──────► stageApproval
                              │                    │
                    (on_done) │        (Enter/Esc)  │
                              ▼                    │
                        stageInput ◄───────────────┘
                              │
                    (on_ask_user)
                              ▼
                        stageAskUser
                              │
                    (Enter/Esc)
                              ▼
                        stageStreaming
```

---

## Backend: Python JSON-RPC Server

**Location:** `src/autocode/backend/server.py`

The Python backend exposes the full agent loop, tools, LLM providers, session management, and slash commands over a JSON-RPC 2.0 protocol. Launched by `autocode serve`.

### Agent Loop

**Location:** `src/autocode/agent/loop.py`

The `AgentLoop` orchestrates multi-turn interactions:
1. Receives user message
2. Sends to LLM with tool definitions
3. LLM responds with text (streamed) and/or tool calls
4. Tool calls go through approval -> execution -> result feedback
5. Loop continues until LLM produces a final text response

Callbacks map to JSON-RPC notifications/requests:

| Callback | JSON-RPC | Direction |
|----------|----------|-----------|
| `on_chunk(text)` | `on_token` notification | Py → Go |
| `on_thinking_chunk(text)` | `on_thinking` notification | Py → Go |
| `on_tool_call(name, status, result)` | `on_tool_call` notification | Py → Go |
| `approval_callback(tool, args)` | `on_tool_request` **request** | Py → Go (waits for response) |
| `ask_user_callback(question, options)` | `on_ask_user` **request** | Py → Go (waits for response) |
| *(loop complete)* | `on_done` notification | Py → Go |

### LLM Providers

**Location:** `src/autocode/layer4/llm.py`

| Provider | Use Case |
|----------|----------|
| `OllamaProvider` | Local inference (default). Connects to `ollama serve` |
| `OpenRouterProvider` | Cloud development backend. Requires API key |

Both implement async streaming via `generate(messages, stream=True)`.

### Tools

**Location:** `src/autocode/agent/tools.py`

The agent has access to filesystem tools (read, write, edit, glob, grep), shell execution, and other coding-assistant tools. Each tool call goes through the approval system before execution.

### Approval System

**Location:** `src/autocode/agent/approval.py`

Three modes:
- **Ask**: Prompt user for every tool call (default)
- **Auto-approve**: Skip prompts (for trusted operations)
- **Session approve**: Remember approval for the rest of the session

Blocked patterns prevent dangerous operations (e.g., `rm -rf /`).

### Session Store

**Location:** `src/autocode/session/store.py`

SQLite-backed (WAL mode) conversation persistence. Stores messages, metadata, and session state. Located at `~/.autocode/sessions.db`.

### Slash Commands

**Location:** `src/autocode/tui/commands.py`

15 commands handled by `CommandRouter`:

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/model [name]` | Show or switch model |
| `/mode [mode]` | Show or switch approval mode |
| `/new [title]` | New session |
| `/sessions` | List sessions |
| `/resume [id]` | Resume a session |
| `/compact` | Compact conversation history |
| `/init` | Initialize project rules |
| `/shell [on/off]` | Toggle shell access |
| `/thinking [on/off]` | Toggle thinking display |
| `/copy` | Copy last response |
| `/clear` | Clear display |
| `/exit` | Exit the application |

Go handles `/exit`, `/clear`, `/thinking` locally. All others are delegated to the Python backend via `command` JSON-RPC request.

---

## JSON-RPC Protocol

Wire format: newline-delimited JSON (one JSON object per line over stdin/stdout).

### Go → Python Requests

| Method | Params | Description |
|--------|--------|-------------|
| `chat` | `{message, session_id}` | Send user message to agent loop |
| `cancel` | `{}` | Cancel current generation |
| `command` | `{cmd}` | Execute slash command |
| `session.new` | `{title}` | Create new session |
| `session.list` | `{}` | List all sessions |
| `session.resume` | `{session_id}` | Resume session |
| `config.get` | `{}` | Get current config |
| `config.set` | `{key, value}` | Set config value |
| `shutdown` | `{}` | Graceful shutdown |

### Python → Go Notifications (no response expected)

| Method | Params | Description |
|--------|--------|-------------|
| `on_token` | `{text}` | Streaming token |
| `on_thinking` | `{text}` | Thinking/reasoning token |
| `on_tool_call` | `{name, status, result, args}` | Tool call status update |
| `on_done` | `{tokens_in, tokens_out}` | Generation complete |
| `on_error` | `{message}` | Error occurred |
| `on_status` | `{model, provider, mode, session_id}` | Backend status info |

### Python → Go Requests (response required)

| Method | Params | Response |
|--------|--------|----------|
| `on_tool_request` | `{tool, args}` | `{approved, session_approve}` |
| `on_ask_user` | `{question, options, allow_text}` | `{answer}` |

### ID Ranges

- Go → Python: monotonic from 1
- Python → Go: monotonic from 1000

---

## 4-Layer Intelligence Model

```
┌─────────────────────────────────────────────┐
│  Layer 4: Full Reasoning (8B LLM)           │
│  Complex edits, multi-file planning         │
│  Latency: 5-30s | Tokens: 2000-8000        │
├─────────────────────────────────────────────┤
│  Layer 3: Constrained Generation (1.5B)     │
│  Grammar-constrained output, completions    │
│  Latency: 500ms-2s | Tokens: 500-2000      │
├─────────────────────────────────────────────┤
│  Layer 2: Retrieval & Context               │
│  Code search, embeddings, project rules     │
│  Latency: 100-500ms | Tokens: 0            │
├─────────────────────────────────────────────┤
│  Layer 1: Deterministic Analysis            │
│  Tree-sitter, LSP, static analysis          │
│  Latency: <50ms | Tokens: 0                │
└─────────────────────────────────────────────┘
```

The system always tries the cheapest layer first and only escalates when necessary. Layers 1-2 use zero LLM tokens.

---

## Directory Structure

```
autocode/
├── rtui/                          # Rust TUI frontend
│   ├── Cargo.toml                 # crossterm + ratatui + tokio + portable-pty
│   ├── Cargo.lock
│   ├── src/
│   │   ├── main.rs                # Entry, arg parsing, raw-mode guard, effect dispatch
│   │   ├── backend/
│   │   │   ├── pty.rs             # portable-pty spawn
│   │   │   └── process.rs         # Child lifecycle + kill-on-drop
│   │   ├── rpc/
│   │   │   ├── codec.rs           # encode/decode JSON lines
│   │   │   ├── protocol.rs        # 16 serde structs
│   │   │   └── bus.rs             # PTY reader + writer tasks (spawn_blocking)
│   │   ├── state/
│   │   │   ├── model.rs           # AppState, Stage, scrollback
│   │   │   ├── effects.rs         # Effect enum
│   │   │   ├── reducer.rs         # Pure reduce() function
│   │   │   └── reducer_tests.rs   # Unit tests
│   │   ├── commands/mod.rs        # Slash-command router
│   │   ├── ui/
│   │   │   ├── composer.rs        # Hand-roll multi-line editor
│   │   │   ├── history.rs         # Frecency history
│   │   │   ├── spinner.rs         # 194 verbs × 4 braille frames
│   │   │   └── event_loop.rs      # crossterm EventStream → Event
│   │   └── render/
│   │       ├── view.rs            # ratatui layout
│   │       └── markdown.rs        # Inline markdown
│   └── tests/                     # LinesCodec spike + design records
├── src/autocode/
│   ├── cli.py                     # CLI entry point (Typer) — launches Rust TUI
│   ├── config.py                  # Configuration (Pydantic)
│   ├── agent/
│   │   ├── loop.py                # Agent loop (multi-turn)
│   │   ├── tools.py               # Tool definitions
│   │   ├── approval.py            # Approval system
│   │   └── prompts.py             # System prompts
│   ├── backend/
│   │   └── server.py              # JSON-RPC server (stdin/stdout)
│   ├── layer4/
│   │   └── llm.py                 # LLM providers
│   ├── session/
│   │   └── store.py               # SQLite session store (WAL)
│   ├── tui/
│   │   ├── app.py                 # Textual fullscreen fallback (--tui)
│   │   └── commands.py            # Slash command router (Python side)
│   └── utils/
│       └── file_tools.py          # File read/write utilities
├── tests/
│   ├── unit/                      # Python unit tests
│   ├── integration/               # Integration tests (require gateway)
│   ├── pty/                       # PTY smoke harnesses + backend stubs
│   ├── tui-comparison/            # Track 1 runtime-invariant harness
│   ├── tui-references/            # Track 4 design-target ratchet
│   └── vhs/                       # Self-vs-self PNG regression
├── docs/qa/                       # Stored verification artifacts
├── Makefile                       # Build targets (make tui-build / tui-regression / tui-references)
├── pyproject.toml                 # Python project config
└── CLAUDE.md                      # AI assistant guidelines
```

---

## Build and Test

### Prerequisites

- Python 3.11+ with [uv](https://docs.astral.sh/uv/)
- Rust toolchain (`rustup install stable`)
- LLM Gateway at `http://localhost:4000/v1` (optional but recommended)

### Build

```bash
# Python
uv sync --all-extras

# Rust TUI
cd autocode/rtui && cargo build --release
# Binary at autocode/rtui/target/release/autocode-tui
```

### Test

```bash
# Python unit tests
uv run pytest autocode/tests/unit/ -v

# Rust TUI tests (59 tests)
cd autocode/rtui && cargo test

# Rust TUI lint
cd autocode/rtui && cargo clippy -- -D warnings
cd autocode/rtui && cargo fmt -- --check

# Python lint
cd autocode && uv run ruff check src/ tests/

# Full TUI matrix (four dimensions — see docs/tui-testing/)
make tui-regression
make tui-references
```

### Run

```bash
# Default: Rust TUI
autocode

# Or via explicit chat subcommand
autocode chat

# Textual fullscreen fallback
autocode chat --tui

# Rich REPL fallback
autocode chat --legacy

# Python backend only (used internally by the Rust TUI via PTY)
uv run autocode serve
```
