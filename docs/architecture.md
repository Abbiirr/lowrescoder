# HybridCoder Architecture

## Overview

HybridCoder is a local-first AI coding assistant that runs on consumer hardware. It uses a **4-layer intelligence model** where classical AI techniques handle the majority of operations, invoking LLMs only when necessary.

The system is split into a **Go TUI frontend** and a **Python backend**, communicating via JSON-RPC 2.0 over stdin/stdout.

```
┌─────────────────────────────────────┐
│         Go TUI Frontend             │
│  (Bubble Tea, inline mode)          │
│                                     │
│  Input ─ Streaming ─ Approvals      │
│  Autocomplete ─ History ─ Markdown  │
└──────────────┬──────────────────────┘
               │ JSON-RPC 2.0
               │ (stdin/stdout, newline-delimited)
┌──────────────┴──────────────────────┐
│         Python Backend              │
│  (hybridcoder serve)                │
│                                     │
│  Agent Loop ─ Tools ─ LLM Providers │
│  Session Store ─ Config ─ Commands  │
└─────────────────────────────────────┘
```

---

## Frontend: Go Bubble Tea TUI

**Location:** `cmd/hybridcoder-tui/`

The Go frontend handles all terminal interaction using Charm's [Bubble Tea](https://github.com/charmbracelet/bubbletea) framework (Elm Architecture). It runs in **inline mode** (no alternate screen) to preserve native terminal scrollback.

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
| `history.go` | Persistent command history (~/.hybridcoder/go_history) |
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

**Location:** `src/hybridcoder/backend/server.py`

The Python backend exposes the full agent loop, tools, LLM providers, session management, and slash commands over a JSON-RPC 2.0 protocol. Launched by `hybridcoder serve`.

### Agent Loop

**Location:** `src/hybridcoder/agent/loop.py`

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

**Location:** `src/hybridcoder/layer4/llm.py`

| Provider | Use Case |
|----------|----------|
| `OllamaProvider` | Local inference (default). Connects to `ollama serve` |
| `OpenRouterProvider` | Cloud development backend. Requires API key |

Both implement async streaming via `generate(messages, stream=True)`.

### Tools

**Location:** `src/hybridcoder/agent/tools.py`

The agent has access to filesystem tools (read, write, edit, glob, grep), shell execution, and other coding-assistant tools. Each tool call goes through the approval system before execution.

### Approval System

**Location:** `src/hybridcoder/agent/approval.py`

Three modes:
- **Ask**: Prompt user for every tool call (default)
- **Auto-approve**: Skip prompts (for trusted operations)
- **Session approve**: Remember approval for the rest of the session

Blocked patterns prevent dangerous operations (e.g., `rm -rf /`).

### Session Store

**Location:** `src/hybridcoder/session/store.py`

SQLite-backed (WAL mode) conversation persistence. Stores messages, metadata, and session state. Located at `~/.hybridcoder/sessions.db`.

### Slash Commands

**Location:** `src/hybridcoder/tui/commands.py`

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
hybridcoder/
├── cmd/
│   └── hybridcoder-tui/       # Go TUI frontend (25 files)
│       ├── go.mod
│       ├── main.go             # Entry point
│       ├── model.go            # Root model
│       ├── view.go             # Rendering
│       ├── update.go           # Message handling
│       ├── backend.go          # Python subprocess manager
│       ├── protocol.go         # JSON-RPC types
│       ├── messages.go         # Bubble Tea messages
│       ├── approval.go         # Tool approval UI
│       ├── askuser.go          # Ask-user prompt UI
│       ├── commands.go         # Slash command parsing
│       ├── completion.go       # Autocomplete
│       ├── history.go          # Command history
│       ├── markdown.go         # Glamour rendering
│       ├── styles.go           # Lip Gloss styles
│       ├── statusbar.go        # Status bar
│       ├── detect.go           # Terminal detection
│       ├── backend_windows.go  # Windows process mgmt
│       ├── backend_unix.go     # Unix process mgmt
│       └── *_test.go           # Tests (7 files)
├── src/hybridcoder/
│   ├── cli.py                  # CLI entry point (Typer)
│   ├── config.py               # Configuration (Pydantic)
│   ├── agent/
│   │   ├── loop.py             # Agent loop (multi-turn)
│   │   ├── tools.py            # Tool definitions
│   │   ├── approval.py         # Approval system
│   │   └── prompts.py          # System prompts
│   ├── backend/
│   │   └── server.py           # JSON-RPC server
│   ├── layer4/
│   │   └── llm.py              # LLM providers (Ollama, OpenRouter)
│   ├── session/
│   │   └── store.py            # SQLite session store
│   ├── tui/
│   │   ├── app.py              # Textual TUI (alternate screen)
│   │   └── commands.py         # Slash command router
│   ├── inline/
│   │   └── app.py              # Python inline REPL (legacy)
│   └── utils/
│       └── file_tools.py       # File read/write utilities
├── tests/
│   ├── unit/                   # Python unit tests
│   └── integration/            # Integration tests (require servers)
├── docs/
│   ├── architecture.md         # This file
│   ├── plan.md                 # Product roadmap
│   ├── archive/                # Superseded/historical docs
│   └── plan/                   # Implementation plans
├── Makefile                    # Build targets
├── pyproject.toml              # Python project config
└── CLAUDE.md                   # AI assistant guidelines
```

---

## Build and Test

### Prerequisites

- Python 3.11+ with [uv](https://docs.astral.sh/uv/)
- Go 1.22+
- [Ollama](https://ollama.com/) (for local LLM inference)

### Build

```bash
# Python
uv sync --all-extras

# Go TUI
make tui
# Or directly:
cd cmd/hybridcoder-tui && go build -o ../../build/hybridcoder-tui .
```

### Test

```bash
# Python tests (569+ tests)
make test

# Go tests (93 tests)
make go-test

# Linting
make lint
```

### Run

```bash
# Default: Go TUI (if built) or Python inline REPL
uv run hybridcoder chat

# Force Go TUI
uv run hybridcoder chat --go-tui

# Force Python inline REPL (legacy)
uv run hybridcoder chat --legacy

# Python backend only (for Go TUI subprocess)
uv run hybridcoder serve
```
