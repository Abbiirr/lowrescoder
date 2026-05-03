# AutoCode Architecture

## Overview

AutoCode is a local-first AI coding assistant that runs on consumer hardware. It uses a **4-layer intelligence model** where classical AI techniques handle the majority of operations, invoking LLMs only when necessary.

The system is split into a **Rust TUI frontend** and a **Python backend**, communicating via newline-delimited JSON-RPC 2.0. The default user path is bare `autocode`, which launches the Rust TUI in spawn-managed mode and starts a backend subprocess over stdio. The same frontend can also attach to an independently started backend over localhost TCP.

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
               │ (stdio subprocess or localhost TCP)
┌──────────────┴───────────────────────────┐
│         Python Backend                   │
│  (autocode serve --transport stdio|tcp)  │
│                                          │
│  Agent Loop ─ Tools ─ LLM Providers      │
│  Session Store ─ Config ─ Commands       │
└──────────────────────────────────────────┘
```

The Go Bubble Tea TUI and the Python prompt-toolkit inline frontend were previous frontends; both were deleted at M11 cutover (2026-04-19). The remaining Python UI surfaces are fallbacks: `autocode chat --tui` for Textual fullscreen and `autocode chat --legacy` for the Rich REPL. See `docs/decisions/ADR-001-rust-tui-migration.md` for the decision record.

---

## Frontend: Rust TUI

**Location:** `autocode/rtui/`
**Binary:** `autocode/rtui/target/release/autocode-tui` (~2.4 MB stripped)
**Stack:** `crossterm` 0.28 + `ratatui` 0.29 + `tokio` 1.x + `portable-pty` 0.8 + `serde_json` + `anyhow` + `tracing`

The Rust frontend handles terminal interaction using ratatui widgets over crossterm. It runs in **inline mode by default** to preserve native terminal scrollback; `autocode --mode altscreen` opts into the alternate-screen Rust TUI. `autocode --attach HOST:PORT` connects the same frontend to an already-running TCP backend. (The earlier `autocode chat --rust-altscreen` flag is no longer canonical; prefer `autocode --mode altscreen`.)

**Reference docs:** [`docs/reference/rust-tui-architecture.md`](reference/rust-tui-architecture.md) and [`docs/reference/rust-tui-rpc-contract.md`](reference/rust-tui-rpc-contract.md).

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Inline mode (no alt-screen) | Preserves native scrollback after exit |
| Spawn-managed stdio backend by default | Keeps bare `autocode` self-contained while preserving frontend/backend separation |
| Attach/TCP mode | Lets the backend and frontend run independently for benchmarking, debugging, and future frontend swaps |
| Reducer/effects state model | Keeps rendering, input, RPC events, and side effects testable in isolation |
| Native Rust modals/pickers | Approval, ask-user, model/provider/session pickers, palette, and recovery are frontend state, not nested Python prompts |
| JSON-RPC schema parity | Python schema and Rust protocol structs track the same newline-delimited contract |

### File Structure

| File | Purpose |
|------|---------|
| `src/main.rs` | Entry point: launch-mode parsing, connection-mode resolution, raw-mode guard, event/effect loop |
| `src/backend/connection.rs` | Spawn-managed vs attach/TCP connection abstraction |
| `src/backend/pty.rs` | Spawn-managed backend subprocess over piped stdio |
| `src/backend/process.rs` | Child lifecycle and kill-on-drop cleanup |
| `src/rpc/codec.rs` | JSON-RPC line encode/decode |
| `src/rpc/protocol.rs` | Rust wire structs for backend notifications/requests |
| `src/rpc/schema.rs` | Canonical method classification for reducer dispatch |
| `src/rpc/bus.rs` | Reader/writer tasks over any backend connection handle |
| `src/state/model.rs` | AppState, Stage, picker models, transcript/task state |
| `src/state/reducer.rs` | Pure reducer for input, RPC events, and frontend state transitions |
| `src/state/effects.rs` | Effect enum for outbound RPC, editor launch, and process actions |
| `src/render/view.rs` | Ratatui layout, status bar, modals, pickers, detail surfaces |
| `src/render/markdown.rs` | Inline markdown rendering |
| `src/ui/composer.rs` | Multi-line composer |
| `src/ui/textbuf.rs` | UTF-8-safe editable text buffer |
| `src/ui/history.rs` | Persistent frecency history (`~/.autocode/history.json`) |
| `src/ui/editor.rs` | External editor launch/return flow |
| `src/ui/event_loop.rs` | crossterm EventStream to app events |
| `src/commands/mod.rs` | Frontend slash/palette command routing |

### UI Stage Machine

```
Idle ──(Enter/chat)──► Streaming ──(tool call)──► ToolCall
  ▲                       │                         │
  │                       ├──(on_tool_request)──► Approval
  │                       ├──(on_ask_user)──────► AskUser
  │                       └──(on_done/error)────► Idle
  │
  ├── Palette
  ├── Picker(Model|Provider|Session)
  ├── EditorLaunch
  └── Shutdown
```

---

## Backend: Python JSON-RPC Server

**Location:** `autocode/src/autocode/backend/`

The Python backend exposes the agent loop, tools, LLM providers, session management, slash commands, tasks, subagents, memory, checkpoints, and config over JSON-RPC 2.0. It is launched automatically by the Rust TUI in spawn-managed stdio mode, or independently with `autocode serve --transport stdio|tcp`.

External agent clients use a separate read-only MCP surface exposed by
`autocode mcp-serve --transport stdio`. Generated Claude Code, Codex, and
OpenCode config snippets point at that command; it supports MCP stdio
`initialize`, `tools/list`, and `tools/call` against the L1/L2 read-only tools.
`autocode doctor` reports MCP readiness and the audit-log path. MCP tool calls
are always available in memory during process lifetime and can be persisted as
JSONL with `--audit-log-path` or `AUTOCODE_MCP_AUDIT_LOG`.

| Module | Responsibility |
|--------|----------------|
| `autocode/src/autocode/backend/server.py` | Backend application state, request dispatch surface, frontend notification helpers |
| `autocode/src/autocode/backend/chat.py` | Chat-turn execution, callback wiring, layer selection, `on_done` shaping |
| `autocode/src/autocode/backend/services.py` | Non-transport command/session/model/provider/task service helpers |
| `autocode/src/autocode/backend/transport.py` | `BackendTransport`, JSON encode/decode, pending frontend-request broker |
| `autocode/src/autocode/backend/stdio_host.py` | Stdio line framing/threading host adapter |
| `autocode/src/autocode/backend/tcp_host.py` | Localhost TCP JSON-RPC host adapter |
| `autocode/src/autocode/backend/schema.py` | Canonical JSON-RPC method names, params, and result models |

### Agent Loop

**Location:** `autocode/src/autocode/agent/loop.py`

The `AgentLoop` orchestrates multi-turn interactions:
1. Receives user message
2. Sends to LLM with tool definitions
3. LLM responds with text (streamed) and/or tool calls
4. Tool calls go through approval -> execution -> result feedback
5. Loop continues until LLM produces a final text response

Callbacks map to JSON-RPC notifications/requests:

| Callback | JSON-RPC | Direction |
|----------|----------|-----------|
| `on_chunk(text)` | `on_token` notification | Py → Rust |
| `on_thinking_chunk(text)` | `on_thinking` notification | Py → Rust |
| `on_tool_call(name, status, result)` | `on_tool_call` notification | Py → Rust |
| `approval_callback(tool, args)` | `on_tool_request` **request** | Py → Rust (waits for response) |
| `ask_user_callback(question, options)` | `on_ask_user` **request** | Py → Rust (waits for response) |
| *(loop complete)* | `on_done` notification | Py → Rust |

### Internal Hook Dispatcher

**Location:** `autocode/src/autocode/agent/hooks.py`

The backend has two hook surfaces:

| Surface | Purpose |
|---|---|
| `HookRegistry` | External Claude-Code-compatible shell hooks loaded from `.claude/settings.json` |
| `HookDispatcher` | Internal ordered hook bus for backend features that need lifecycle integration without adding more ad-hoc branches to `AgentLoop` |

`HookDispatcher` is created by the shared factory and injected into `AgentLoop`.
It dispatches `pre_turn`, `post_turn`, `on_token`, `pre_tool_call`,
`post_tool_call_success`, `post_tool_call_success_async`, and
`post_tool_call_error`.

Dispatcher calls are ordered and exception-isolated: one bad hook is skipped
without breaking the agent loop. Success hooks may return an augmented tool
result, which is chained through later hooks before the result is stored or
shown to the frontend. Current internal hook adapters cover scratch offload,
git-aware staging, per-tool checkpoints, and post-edit auto-verify.

### LLM Providers

**Location:** `autocode/src/autocode/layer4/llm.py`

| Provider | Use Case |
|----------|----------|
| `OllamaProvider` | Local inference (default). Connects to `ollama serve` |
| `OpenRouterProvider` | OpenRouter or OpenAI-compatible gateway path. Requires API key/gateway config |

Both implement async streaming and tool-calling through `generate_with_tools()`, with thinking/reasoning token streaming surfaced through `on_thinking`.

### Tools

**Location:** `autocode/src/autocode/agent/tools.py`

The agent has a 38-tool registry. Sixteen core tools are sent to the model by default, while deferred tools are discoverable through `tool_search` to reduce token pressure. Write/shell tools go through approval and hard-block checks before execution.

### Approval System

**Location:** `autocode/src/autocode/agent/approval.py`

Four modes:
- **read-only**: block mutating and shell operations
- **suggest**: ask before mutating or shell operations
- **auto**: auto-approve ordinary operations while respecting hard blocks
- **autonomous**: least restrictive mode while still respecting hard blocks

Blocked shell patterns and dangerous write paths/content are enforced before handlers run.

### Session Store

**Location:** `autocode/src/autocode/session/store.py`

SQLite-backed (WAL mode) conversation persistence. Stores messages, metadata, and session state. Located at `~/.autocode/sessions.db`.

### Slash Commands

**Location:** `autocode/src/autocode/app/commands.py`

29 backend-visible commands are handled by `CommandRouter` and exposed to the Rust TUI through `command.list`:

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/model [name]` | Show or switch model |
| `/provider [name]` | Show or switch provider |
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
| `/cost [--detail]` | Show session cost and token accounting |
| `/memory` | Show session memory |
| `/checkpoint` | Save/list/restore checkpoints |
| `/tasks` | Show tasks/subagents |
| `/plan` | Show or switch planning mode |
| `/review`, `/diff`, `/grep`, `/cc`, `/restore`, `/escalation` | Open dedicated Rust TUI detail/picker surfaces |

The Rust TUI owns local UI-only surfaces such as palette/pickers and recovery display, but backend command semantics are returned through `command` / `command.list`.

---

## JSON-RPC Protocol

Wire format: newline-delimited JSON (one JSON object per line) over either stdio pipes or localhost TCP.

### Rust → Python Requests

| Method | Params | Description |
|--------|--------|-------------|
| `chat` | `{message, session_id}` | Send user message to agent loop |
| `cancel` | `{}` | Cancel current generation |
| `command` | `{cmd}` | Execute slash command |
| `command.list` | `{}` | List backend-owned slash commands for overlays |
| `session.new` | `{title}` | Create new session |
| `session.list` | `{}` | List all sessions |
| `model.list` | `{}` | List models for picker/autocomplete surfaces |
| `provider.list` | `{}` | List providers for picker/autocomplete surfaces |
| `session.resume` | `{session_id}` | Resume session |
| `task.list` | `{}` | List task projection |
| `subagent.list` | `{}` | List subagent projection |
| `subagent.cancel` | `{subagent_id}` | Cancel subagent |
| `plan.status` | `{}` | Get plan mode status |
| `plan.set` | `{mode}` | Set plan mode |
| `config.get` | `{}` | Get current config |
| `config.set` | `{key, value}` | Set config value |
| `memory.list` | `{}` | List session memory |
| `checkpoint.list` | `{}` | List checkpoints |
| `checkpoint.restore` | `{}` | Restore checkpoint |
| `plan.export` | `{}` | Export plan artifact |
| `plan.sync` | `{}` | Sync plan/task state |
| `steer` | `{message}` | Send steering text during an active turn |
| `session.fork` | `{}` | Fork current session |
| `shutdown` | `{}` | Graceful shutdown |

### Python → Rust Notifications (no response expected)

| Method | Params | Description |
|--------|--------|-------------|
| `on_token` | `{text}` | Streaming token |
| `on_thinking` | `{text}` | Thinking/reasoning token |
| `on_tool_call` | `{name, status, result, args}` | Tool call status update |
| `on_done` | `{tokens_in, tokens_out, cancelled, layer_used}` | Generation complete |
| `on_error` | `{message}` | Error occurred |
| `on_warning` | `{message}` | Non-fatal warning |
| `on_chat_ack` | `{request_id, session_id}` | Chat request accepted/session resolved |
| `on_status` | `{model, provider, mode, session_id}` | Backend status info |
| `on_task_state` | `{tasks, subagents}` | Background-task state update |
| `on_cost_update` | `{cost, tokens_in, tokens_out}` | Per-turn cost/token snapshot |

### Python → Rust Requests (response required)

| Method | Params | Response |
|--------|--------|----------|
| `on_tool_request` | `{tool, args}` | `{approved, session_approve}` |
| `on_ask_user` | `{question, options, allow_text}` | `{answer}` |

`docs/reference/rpc-schema-v1.md` is the canonical contract; this section is an overview.

### ID Ranges

- Frontend → backend: monotonic from 1
- Backend → frontend: monotonic from 1000

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

Java LSP support is registered through `autocode.layer2.lsp_servers.java.JavaLSPAdapter`. It maps `.java` files to `jdtls`, keeps startup lazy through the shared subprocess LSP client, and reports `jdtls` plus Java 17+ runtime readiness through `autocode doctor` without spawning the language server. Tests assert only project-local symbols so results do not depend on JDK source or Javadoc availability.

JavaScript and TypeScript LSP support use `typescript-language-server --stdio` through separate adapter classes for explicit routing: `.js` / `.jsx` / `.mjs` map to JavaScript, and `.ts` / `.tsx` / `.d.ts` map to TypeScript. Both adapters share non-spawning readiness metadata for the server and `typescript` peer dependency; TypeScript adds type-diagnostic initialization metadata.

C, Kotlin, and Python LSP support follow the same adapter pattern. C maps `.c` / `.h` to `clangd` with `compile_commands.json` discovery, Kotlin maps `.kt` / `.kts` to `kotlin-language-server` with an extended timeout and Java runtime readiness, and Python maps `.py` / `.pyi` to `pylsp` while preserving the existing Jedi-backed `lsp_*` tools as a fallback path for one release.

Go and Rust complete the current eight-language LSP adapter matrix. Go maps `.go` files to `gopls` with `go.mod` discovery and Go 1.16+ readiness metadata. Rust maps `.rs` files to `rust-analyzer` with `Cargo.toml` discovery, rustup component readiness metadata, clippy-diagnostics initialization metadata, and an extended cold-cache timeout.

The agent runtime consumes that LSP substrate through post-edit auto-verify. After a successful filesystem-mutating tool call, `AgentLoop` extracts touched files, runs `autocode.agent.auto_verify.verify_after_edit(...)` for files with registered adapters, and appends normalized diagnostics to the tool result. Unsupported languages are skipped, `/verify on|off|status` controls the feature, persistent failures do not roll back automatically, and the existing checkpoint/rollback path remains user-confirmable.

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
│   │   │   ├── connection.rs      # spawn-managed vs attach/TCP backend selection
│   │   │   ├── pty.rs             # spawn-managed stdio backend process
│   │   │   └── process.rs         # Child lifecycle + kill-on-drop
│   │   ├── rpc/
│   │   │   ├── codec.rs           # encode/decode JSON lines
│   │   │   ├── protocol.rs        # serde structs for protocol payloads
│   │   │   ├── schema.rs          # canonical method classification
│   │   │   └── bus.rs             # backend reader + writer tasks
│   │   ├── state/
│   │   │   ├── model.rs           # AppState, Stage, transcript, pickers
│   │   │   ├── effects.rs         # Effect enum
│   │   │   ├── reducer.rs         # Pure reduce() function
│   │   │   └── reducer_tests.rs   # Unit tests
│   │   ├── commands/mod.rs        # Frontend slash-command/palette router
│   │   ├── ui/
│   │   │   ├── composer.rs        # Hand-roll multi-line editor
│   │   │   ├── textbuf.rs         # UTF-8-safe text buffer
│   │   │   ├── editor.rs          # External editor handoff
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
│   │   ├── server.py              # Backend app + dispatch surface
│   │   ├── chat.py                # Chat-turn execution and callbacks
│   │   ├── services.py            # Command/session/model/task services
│   │   ├── transport.py           # JSON-RPC transport protocol helpers
│   │   ├── stdio_host.py          # Stdio host adapter
│   │   └── tcp_host.py            # Localhost TCP host adapter
│   ├── layer4/
│   │   └── llm.py                 # LLM providers
│   ├── session/
│   │   └── store.py               # SQLite session store (WAL)
│   ├── tui/
│   │   └── app.py                 # Textual fullscreen fallback (--tui)
│   ├── app/
│   │   └── commands.py            # Backend slash command router
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

# Rust TUI tests
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

# Explicit Rust TUI launch mode override
autocode --mode inline
autocode --mode altscreen

# Attach frontend to an independently running backend
uv run autocode serve --transport tcp --host 127.0.0.1 --port 8765
autocode --attach 127.0.0.1:8765

# Textual fullscreen fallback
autocode chat --tui

# Rich REPL fallback
autocode chat --legacy

# Python backend over stdio, used internally by the Rust TUI spawn-managed path
uv run autocode serve --transport stdio

# Read-only MCP stdio server for external agent clients
uv run autocode mcp-serve --transport stdio --audit-log-path ~/.autocode/mcp_audit.jsonl
```
