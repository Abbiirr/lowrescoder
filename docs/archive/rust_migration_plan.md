# Rust TUI Migration Plan

> **Status:** ACTIVE — all 12 decisions locked 2026-04-19 (user, Entry 1220). Codex APPROVE Entry 1229.
> **Scope:** Replace `autocode/cmd/autocode-tui/` (Go, BubbleTea, 30 files, 13,102 LOC) with a Rust inline TUI binary at `autocode/rtui/` speaking the **unchanged** JSON-RPC protocol to the **unchanged** Python backend.
> **Authority:** `PLAN.md §1h` is the canonical authority. This file and `rust_migration_todo.md` are builder-oriented extracts that must stay in sync with it. On any conflict, `PLAN.md §1h` wins. Future §1h updates must be mirrored here.
> **Research source:** `deep-research-report (1).md` (treat as draft; `PLAN.md §1h.2` corrections supersede it).

---

## 1. Strategic Context

### 1.1 Why Migrate

Three concrete gains from Rust — no others are claimed:

1. **Richer terminal control depth** — `crossterm` exposes raw-mode, cursor, synchronized-update, and bracketed-paste primitives directly. BubbleTea v2 abstracts these away, making fine-grained rendering and future capability additions harder.

2. **Linux-first PTY with a credible Windows path** — `portable-pty` (WezTerm's crate) provides a uniform Linux PTY + Windows ConPTY API. When Windows work begins (post-v1), the PTY spawn code needs no architectural change.

3. **Smaller long-tail maintenance surface** — one Rust binary, one `Cargo.lock`. Eliminates Go runtime, CGO concerns, and BubbleTea version-churn.

**What is NOT a new Rust benefit:**
- Inline-by-default scrollback preservation — the Go TUI already defaults to inline mode (`main.go:13-20`; `--altscreen` is opt-in since commit `b113adb`). Rust preserves this behavior, it does not introduce it.

### 1.2 What Stays Unchanged

- Python backend (`autocode/src/autocode/backend/server.py`, agent loop, session store, tool surface, hooks, skills).
- JSON-RPC protocol as defined in `autocode/cmd/autocode-tui/protocol.go` — Rust must be semantically indistinguishable on the wire (same method, id, params/result, event order). See §6.
- Four-dimension TUI testing matrix (Track 1 · Track 4 · VHS · PTY smoke) — all four retarget the Rust binary via `$AUTOCODE_TUI_BIN`. See §9.
- Artifact storage policy: `autocode/docs/qa/test-results/<YYYYMMDD-HHMMSS>-<label>.md`.
- Agent communication protocol, commit policy, role defaults.

### 1.3 What Gets Deleted (at Rust-M11 Cutover)

- `autocode/cmd/autocode-tui/` — Go TUI deleted entirely.
- `autocode/src/autocode/inline/app.py` + `renderer.py` + `completer.py` + `__init__.py` — Python REPL fallback deleted.
- No coexistence period. No `AUTOCODE_FRONTEND` selector. One binary: `autocode-tui`.

### 1.4 Platform Matrix

| Platform | v1 Status | Notes |
|---|---|---|
| Linux x86_64 | **REQUIRED** | xterm, Ghostty, kitty, alacritty, gnome-terminal, tmux |
| macOS (any arch) | **NEVER** | Out of scope for all versions |
| Windows x86_64 | post-v1 | Keep architecture ConPTY-capable; do not build toward it during M1–M11 |

### 1.5 All 12 Locked Decisions

| # | Decision | Answer |
|---|---|---|
| a | Strategic go/no-go | **YES — migrate Go → Rust** |
| b | Crate stack (baseline) | `crossterm + ratatui + tokio + portable-pty + serde_json + anyhow + tracing`. M1 spikes: `tui-textarea`, `tokio-util::LinesCodec` |
| c | PTY vs plain pipe | **PTY via `portable-pty`** |
| d | §1f Milestone C/D/E/F timing | **FREEZE** — Go gates stopped; absorbed into Rust-M5 through M10 |
| e | Binary naming | **`autocode-tui`** from day one; Go removed, no coexistence |
| f | Inline vs alt-screen | **INLINE by default**; `--altscreen` opt-in flag |
| g | Platform | **Linux only for v1**; ConPTY path kept open; macOS never; Windows post-v1 |
| h | Selection mechanism | **N/A** — one binary, no selector needed |
| i | Track 4 fidelity | **Permission to improve** — re-baseline `strict=True` xfails at cutover |
| j | Builder agent | **Flexible** — OpenCode or Claude per slice; user decides per milestone |
| k | Python `--inline` fallback | **DELETE** at cutover (git preserves history) |
| l | Research report status | **DRAFT** — `PLAN.md §1h.2` corrections are authoritative |

### 1.6 Build-and-Replace Strategy

No coexistence period. During M1–M10, Go TUI remains frozen (maintenance-only) as the production binary. Rust binary exists under `autocode/rtui/` but is not the production default — developers reach it via `$AUTOCODE_TUI_BIN`. At M11, Go is removed and Rust becomes the only binary.

If Rust-M1–M9 reveal a blocking problem: fix the problem. Go TUI does NOT receive new features as a compensating fallback. If the problem is fatal to the migration, the user decides whether to abandon §1h entirely and unfreeze Go milestones.

---

## 2. Architecture

### 2.1 System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   Rust TUI (autocode-tui)                   │
│                                                             │
│  ┌──────────────┐   ┌────────────────┐   ┌──────────────┐  │
│  │ Input Router │──▶│ Reducer (pure) │──▶│ Render (pull)│  │
│  │ (crossterm   │   │ (AppState,     │   │ (ratatui /   │  │
│  │  EventStream)│   │  Event)→       │   │  crossterm)  │  │
│  └──────┬───────┘   │  (AppState,    │   └──────────────┘  │
│         │           │   Vec<Effect>) │                      │
│         │           └────────┬───────┘                      │
│         │                    │                              │
│         ▼                    ▼                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │          RPC Bus (tokio mpsc channels)               │   │
│  │  event_tx ──→ main task ──→ rpc_tx                  │   │
│  └─────────┬─────────────────────────┬──────────────────┘   │
│  PTY reader│(spawn_blocking)         │PTY writer             │
│  (blocking │ Read)                   │(blocking Write)       │
│            ▼                         ▼                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │    portable-pty master (PTY I/O, resize, monitor)   │   │
│  └────────────────────────┬─────────────────────────────┘   │
└───────────────────────────┼────────────────────────────────┘
                            │ framed JSON, 1 msg/line, LF
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Python backend (UNCHANGED)                                  │
│  autocode/src/autocode/backend/server.py                     │
│  • agent loop  • session store  • tools  • hooks  • skills  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Key Architectural Invariants

1. **The RPC wire format is frozen.** Any Rust-side change that alters a field name, type, or ordering breaks Python. Conformance tests (§9) enforce this gate.
2. **The Rust process owns stdin/stdout raw mode;** the Python child runs inside a PTY and produces JSON on its stdout. Raw mode is enabled on Rust startup before any PTY spawn.
3. **The state machine is a pure reducer** — `fn reduce(state: AppState, event: Event) -> (AppState, Vec<Effect>)` — testable without a terminal or network.
4. **Rendering is pull-based from state** — no render calls from inside the input router, RPC decoder, or PTY monitor tasks.
5. **PTY I/O is blocking; tokio channels are async.** `portable-pty`'s `try_clone_reader()` and `take_writer()` return blocking `Read`/`Write` handles — they MUST live in `tokio::task::spawn_blocking` threads, not in async tasks.

### 2.3 Module Layout

```
autocode/rtui/
├── Cargo.toml                     # workspace member
├── Cargo.lock                     # committed
├── README.md                      # build + run + contributor setup
├── rustfmt.toml
├── .clippy.toml
└── src/
    ├── main.rs                    # CLI args, raw-mode RAII guard, tokio runtime
    ├── state/
    │   ├── mod.rs
    │   ├── model.rs               # AppState struct (see §3)
    │   ├── reducer.rs             # pure reduce() fn
    │   └── effects.rs             # Effect enum
    ├── event_loop.rs              # crossterm EventStream → event_tx
    ├── rpc/
    │   ├── mod.rs
    │   ├── protocol.rs            # all 16 serde structs (see §6)
    │   ├── codec.rs               # line encode/decode, LF framing
    │   └── bus.rs                 # inbound + outbound tasks, request correlation table
    ├── backend/
    │   ├── mod.rs
    │   ├── pty.rs                 # portable-pty spawn, resize, EOF detect
    │   └── process.rs             # child lifecycle: monitor, kill-on-drop
    ├── ui/
    │   ├── mod.rs
    │   ├── composer.rs            # multi-line input, Alt+Enter, history recall
    │   ├── statusbar.rs           # status bar widget
    │   ├── spinner.rs             # 187 verbs, 100ms tick rotation
    │   ├── taskpanel.rs           # on_tasks visualization
    │   ├── completion.rs          # @path expansion + fuzzy match
    │   ├── styles.rs              # color palette (Tokyo Night)
    │   ├── pickers/
    │   │   ├── mod.rs             # PickerState, PickerKind, shared logic
    │   │   ├── model.rs           # /model picker
    │   │   ├── provider.rs        # /provider picker
    │   │   └── session.rs         # /sessions picker
    │   └── prompts/
    │       ├── approval.rs        # blocking approval modal
    │       └── askuser.rs         # ask_user modal
    ├── render/
    │   ├── mod.rs
    │   ├── view.rs                # top-level ratatui widget tree
    │   └── markdown.rs            # inline code/bold/italic/links
    ├── commands/
    │   ├── mod.rs                 # slash command router
    │   ├── clear.rs
    │   ├── exit.rs
    │   ├── fork.rs
    │   ├── compact.rs
    │   ├── plan.rs
    │   ├── sessions.rs
    │   ├── resume.rs
    │   ├── model.rs
    │   ├── provider.rs
    │   └── help.rs
    ├── history.rs                 # frecency scoring (port from history.go)
    └── terminal_detect.rs         # terminal capability probe
tests/
    ├── milestone_a/               # 62 ported runtime invariant scenarios
    ├── palette/                   # Ctrl+K palette scenarios
    ├── unit/                      # per-module unit tests
    └── rpc-conformance/           # Go wire trace replay + semantic parity check
```

---

## 3. State Machine

### 3.1 AppState Fields

```rust
/// Top-level application state. All mutation happens inside reduce().
pub struct AppState {
    // --- Stage ---
    pub stage: Stage,

    // --- Content buffers ---
    pub scrollback: VecDeque<StyledLine>,   // bounded 10_000 lines
    pub stream_buf: String,                  // live token accumulator
    pub stream_lines: Vec<String>,           // stream_buf split on \n

    // --- Composer ---
    pub composer_text: String,
    pub composer_cursor: usize,              // byte offset
    pub composer_lines: Vec<String>,         // for multi-line display
    pub followup_queue: VecDeque<String>,    // queued messages for auto-send on on_done

    // --- History ---
    pub history: Vec<HistoryEntry>,          // frecency-sorted
    pub history_cursor: Option<usize>,       // None = not browsing

    // --- Status bar ---
    pub status: StatusInfo,

    // --- Spinner ---
    pub spinner_frame: u8,                   // 0..=3, cycles ⠋⠙⠹⠸
    pub spinner_verb_idx: usize,             // 0..=186, wraps around

    // --- Tool call display ---
    pub current_tool: Option<ToolCallInfo>,

    // --- Task panel ---
    pub tasks: Vec<TaskEntry>,
    pub subagents: Vec<SubagentEntry>,

    // --- Overlays ---
    pub picker: Option<PickerState>,
    pub palette: Option<PaletteState>,
    pub approval: Option<ApprovalRequest>,
    pub ask_user: Option<AskUserRequest>,

    // --- Error display ---
    pub error_banner: Option<String>,

    // --- Feature flags ---
    pub plan_mode: bool,
    pub altscreen: bool,

    // --- Terminal geometry ---
    pub terminal_size: (u16, u16),           // (cols, rows)

    // --- RPC correlation ---
    pub pending_requests: HashMap<i64, PendingRequest>,
    pub next_request_id: i64,               // monotonically increasing
}

pub enum Stage {
    Idle,
    Streaming,
    ToolCall,
    Approval,         // waiting for user to approve/deny a tool
    AskUser,          // waiting for user to answer a question
    Picker(PickerKind),
    Palette,
    EditorLaunch,     // editor is open; raw mode suspended
    Shutdown,
}

pub struct StatusInfo {
    pub model: String,
    pub provider: String,
    pub mode: String,
    pub session_id: Option<String>,
    pub tokens_in: u32,
    pub tokens_out: u32,
    pub cost: Option<String>,      // formatted string from on_cost_update
    pub bg_tasks: u32,
}

pub struct HistoryEntry {
    pub text: String,
    pub last_used_ms: i64,         // Unix ms
    pub use_count: u32,
}

pub struct ToolCallInfo {
    pub name: String,
    pub status: String,
    pub args: Option<String>,
    pub result: Option<String>,
}

pub struct PickerState {
    pub kind: PickerKind,
    pub entries: Vec<String>,      // all available entries
    pub filter: String,            // current type-to-filter input
    pub cursor: usize,             // index into visible entries
}

pub enum PickerKind { Model, Provider, Session }

pub struct PaletteState {
    pub filter: String,
    pub cursor: usize,
}

pub struct ApprovalRequest {
    pub rpc_id: i64,               // must correlate in ApprovalResult response
    pub tool: String,
    pub args: String,
}

pub struct AskUserRequest {
    pub rpc_id: i64,
    pub question: String,
    pub options: Vec<String>,
    pub allow_text: bool,
    pub selected: usize,           // for option-list navigation
    pub free_text: String,         // for free-text answer
}

pub struct PendingRequest {
    pub method: String,
    pub sent_at: std::time::Instant,
}
```

### 3.2 Event Enum

```rust
pub enum Event {
    // Terminal input
    Key(crossterm::event::KeyEvent),
    Resize(u16, u16),
    Tick,                          // 100ms periodic timer

    // RPC from Python backend (parsed from PTY)
    RpcNotification(RPCMessage),   // id=null, method set
    RpcResponse(RPCMessage),       // id set, method empty
    RpcInboundRequest(RPCMessage), // id set, method set (approval / ask_user)

    // PTY lifecycle
    BackendExit(i32),              // child process exit code
    BackendError(String),          // I/O error reading from PTY

    // Internal
    EditorDone(String),            // editor temp file contents after $EDITOR exits
}
```

### 3.3 Effect Enum

```rust
pub enum Effect {
    // RPC output
    SendRpc(RPCMessage),           // write to PTY writer channel

    // Rendering
    Render,                        // trigger a full redraw

    // Terminal control
    SetRawMode(bool),              // false before editor, true after
    ResizePty(u16, u16),          // propagate resize to PTY child
    EnterAltScreen,
    LeaveAltScreen,

    // OS operations
    SpawnEditor(String),           // open $EDITOR with content; sends EditorDone on exit
    ResizePty(u16, u16),

    // Lifecycle
    Quit,                          // initiate graceful shutdown
}
```

### 3.4 Reducer Signature

```rust
/// Pure function. No I/O. No side effects. Fully unit-testable.
pub fn reduce(state: AppState, event: Event) -> (AppState, Vec<Effect>)
```

All state transitions happen here. Effects are collected and applied by the main task loop after `reduce()` returns.

---

## 4. Async Architecture

### 4.1 Concurrent Tasks

Five concurrent units of execution:

| Unit | Type | Owns | Reads from | Writes to |
|---|---|---|---|---|
| Main task | `tokio::task` | `AppState`, ratatui terminal | `event_rx` | `rpc_tx`, terminal |
| Key reader | `tokio::task` | `crossterm::event::EventStream` | Terminal stdin | `event_tx` |
| PTY reader | `spawn_blocking` | PTY master `Read` handle | PTY master | `event_tx` |
| PTY writer | `spawn_blocking` | PTY master `Write` handle | `rpc_rx` | PTY master |
| Tick task | `tokio::task` | `tokio::time::interval` | Timer | `event_tx` |

### 4.2 Channel Topology

```
event_tx ──────────────────────────────────────────▶ event_rx (main task)
  ▲   ▲   ▲   ▲
  │   │   │   │
  │   │   │   └── tick task
  │   │   └────── key reader
  │   └────────── PTY reader (spawn_blocking)
  └────────────── main task (EditorDone after editor exits)

rpc_tx ─────────────────────────────────────────────▶ rpc_rx (PTY writer)
  ▲
  │
  └── main task (from Effect::SendRpc)
```

### 4.3 PTY I/O Threading Rules

`portable-pty`'s reader and writer are **blocking** — they implement `std::io::Read` and `std::io::Write`, not `AsyncRead`/`AsyncWrite`. Wrapping them in `tokio::io` adapters does NOT work reliably. The correct approach:

```rust
// PTY reader — lives entirely in spawn_blocking
let reader = pty_master.try_clone_reader()?;  // blocking Read
tokio::task::spawn_blocking(move || {
    let buf = BufReader::new(reader);
    for line in buf.lines() {
        let msg: RPCMessage = serde_json::from_str(&line?)?;
        event_tx.blocking_send(Event::from_rpc(msg))?;
    }
    // EOF → send BackendExit
});

// PTY writer — lives entirely in spawn_blocking
let writer = pty_master.take_writer()?;       // blocking Write
tokio::task::spawn_blocking(move || {
    let mut writer = BufWriter::new(writer);
    while let Some(msg) = rpc_rx.blocking_recv() {
        let json = serde_json::to_string(&msg)?;
        writeln!(writer, "{}", json)?;
        writer.flush()?;
    }
});
```

### 4.4 Raw Mode Lifecycle

```
startup:
  enable_raw_mode()
  hide_cursor()
  [optional] enter_alt_screen() if --altscreen

shutdown:
  [optional] leave_alt_screen() if --altscreen
  show_cursor()
  disable_raw_mode()
  kill PTY child (SIGHUP or kill())
```

Raw mode MUST be disabled even on panic. Use a RAII guard struct that disables raw mode in `Drop`.

For `$EDITOR` launch:
1. `disable_raw_mode()` + `show_cursor()`
2. `std::process::Command::new(editor).arg(tempfile).status()` — blocking call
3. Read tempfile contents
4. `enable_raw_mode()` + `hide_cursor()`
5. Send `Event::EditorDone(contents)` to the main task

---

## 5. Crate Stack

### 5.1 Locked Baseline

| Layer | Crate | Version pinning | Rationale |
|---|---|---|---|
| Terminal I/O | `crossterm` | **Pin to ratatui's semver range** (see R11) | Cross-platform; `EventStream` feature; default ratatui backend; ConPTY-capable |
| Layout + widgets | `ratatui` | latest stable | Frame/Widget tree; List, Paragraph, Block; 2–3× less render code vs raw |
| Async runtime | `tokio` | `tokio = { features = ["full"] }` | `spawn_blocking`, `mpsc`, `time::interval`; industry standard |
| PTY spawn | `portable-pty` | latest stable | WezTerm's crate; Linux + ConPTY; blocking read/write (see §4.3) |
| JSON codec | `serde` + `serde_json` | `serde = { features = ["derive"] }` | Struct-per-message mirrors `protocol.go` |
| Errors | `anyhow` | latest stable | Ergonomic error propagation; no perf overhead |
| Logging | `tracing` + `tracing-subscriber` | latest stable | **File only** — stdout is the RPC channel |

**Critical logging rule:** `tracing-subscriber` MUST be configured to write to a file (e.g. `~/.autocode/tui.log`), not stdout. A single `info!()` macro call to stdout will corrupt the RPC protocol.

### 5.2 Cargo.toml Skeleton

```toml
[package]
name = "autocode-tui"
version = "0.1.0"
edition = "2021"
publish = false

[dependencies]
crossterm = { version = "0.28", features = ["event-stream"] }  # must match ratatui
ratatui = "0.29"
tokio = { version = "1", features = ["full"] }
portable-pty = "0.8"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
anyhow = "1"
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }

[dev-dependencies]
# tui-textarea listed as dev-dependency until M1 spike is resolved
tui-textarea = { version = "0.7", optional = true }

[profile.release]
opt-level = 3
lto = "thin"
strip = true
```

**Note on crossterm pinning (Risk R11):** If `ratatui` requires `crossterm 0.28`, your direct `crossterm` dependency must also be `"0.28"`. Two different semver-incompatible versions of crossterm in the same binary create separate raw-mode state — enabling raw mode in one version does not affect the other. Use `cargo tree | grep crossterm` to verify a single version is resolved.

### 5.3 M1 Spike Candidates

These are NOT locked. The M1 spike must produce a verdict before they can be added to `Cargo.toml`:

#### tui-textarea (Risk R10)

`tui-textarea` ships default keybindings that collide with app-owned controls:

| Default keybinding | App-owned meaning |
|---|---|
| `Ctrl+K` | Open command palette |
| `Ctrl+C` | Cancel / steer / exit |
| `Ctrl+J` | Confirm/newline |
| `Ctrl+U` | Clear line |
| `Ctrl+R` | Frecency history search |

Spike question: **Can every default keybinding be suppressed and all key events routed through the app reducer first?**

If yes → promote to locked stack as composer widget.
If no → hand-roll the composer: a simple `Vec<char>` line buffer with cursor tracking is ~100 LOC for M4 and has zero surprise behavior.

#### tokio-util::LinesCodec

`tokio-util::LinesCodec` silently discards bytes when a line exceeds `max_length` (until the next `\n`). This would silently truncate large RPC messages (e.g., `on_tool_call` with a large `result` field).

Spike question: **What is the maximum observed RPC message size? Can we set an explicit cap that is never exceeded?**

Measure by replaying real session wire traces. If max observed < 1 MB, set cap to 4 MB with a hard error (not silent discard). If the RPC protocol can produce unbounded messages (e.g., file-read results), use a manual line-split instead.

---

## 6. JSON-RPC Contract (Frozen)

The wire format is frozen. Rust MUST NOT change any field name, type, or framing rule. Changes to the protocol happen in a separate plan.

### 6.1 Framing Invariants

- One JSON object per line.
- UTF-8 encoding, LF-terminated (`\n` — not `\r\n`).
- `"jsonrpc": "2.0"` required on every message.
- Notification: `id` absent or null, `method` set.
- Request: `id` set (integer), `method` set.
- Response: `id` set, `method` absent.
- Error response: `{"jsonrpc":"2.0","id":N,"error":{"code":C,"message":"..."}}`

### 6.2 Rust Serde Structs (complete)

```rust
use serde::{Deserialize, Serialize};

/// Union type for all JSON-RPC messages on the wire.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RPCMessage {
    pub jsonrpc: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub id: Option<i64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub method: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub params: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<RPCError>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RPCError {
    pub code: i32,
    pub message: String,
}

// --- Notification params (Python → Rust) ---

#[derive(Debug, Deserialize)]
pub struct TokenParams { pub text: String }

#[derive(Debug, Deserialize)]
pub struct ThinkingParams { pub text: String }

#[derive(Debug, Deserialize)]
pub struct DoneParams {
    pub tokens_in: u32,
    pub tokens_out: u32,
    #[serde(default)]
    pub cancelled: bool,
    #[serde(default)]
    pub layer_used: u32,
}

#[derive(Debug, Deserialize)]
pub struct ToolCallParams {
    pub name: String,
    pub status: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub args: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct ErrorParams { pub message: String }

#[derive(Debug, Deserialize)]
pub struct StatusParams {
    pub model: String,
    pub provider: String,
    pub mode: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub session_id: Option<String>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct TaskStateParams {
    pub tasks: Vec<TaskEntry>,
    pub subagents: Vec<SubagentEntry>,
}

/// on_cost_update — OMITTED in research report; present in protocol.go:181-186
#[derive(Debug, Deserialize)]
pub struct CostUpdateParams {
    pub cost: String,
    pub tokens_in: u32,
    pub tokens_out: u32,
}

// --- Inbound request params (Python → Rust, with ID) ---

#[derive(Debug, Deserialize)]
pub struct ApprovalRequestParams {
    pub tool: String,
    pub args: String,
}

#[derive(Debug, Deserialize)]
pub struct AskUserRequestParams {
    pub question: String,
    #[serde(default)]
    pub options: Vec<String>,
    #[serde(default)]
    pub allow_text: bool,
}

// --- Outbound request params (Rust → Python) ---

#[derive(Debug, Serialize)]
pub struct ChatParams {
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub session_id: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct CancelParams {}

#[derive(Debug, Serialize)]
pub struct CommandParams { pub cmd: String }

#[derive(Debug, Serialize)]
pub struct SessionNewParams {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub title: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct SessionResumeParams { pub session_id: String }

#[derive(Debug, Serialize)]
pub struct SessionListParams {}

#[derive(Debug, Deserialize)]
pub struct SessionListResult { pub sessions: Vec<SessionInfo> }

#[derive(Debug, Deserialize, Clone)]
pub struct SessionInfo {
    pub id: String,
    pub title: String,
    pub model: String,
    pub provider: String,
}

#[derive(Debug, Serialize)]
pub struct ForkSessionParams {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub session_id: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct ForkSessionResult { pub new_session_id: String }

#[derive(Debug, Serialize)]
pub struct ConfigSetParams { pub key: String, pub value: String }

#[derive(Debug, Serialize)]
pub struct SteerParams { pub message: String }

// --- Response types (Rust → Python) ---

#[derive(Debug, Serialize)]
pub struct ApprovalResult {
    pub approved: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub session_approve: Option<bool>,
}

#[derive(Debug, Serialize)]
pub struct AskUserResult { pub answer: String }
```

### 6.3 All 16 Message Types (Complete Table)

**Notifications (Python → Rust, id=null):**

| Method | Params type | Source in protocol.go |
|---|---|---|
| `on_token` | `TokenParams` | lines 43–46 |
| `on_thinking` | `ThinkingParams` | lines 48–51 |
| `on_done` | `DoneParams` | lines 53–59 |
| `on_tool_call` | `ToolCallParams` | lines 61–67 |
| `on_error` | `ErrorParams` | lines 69–72 |
| `on_status` | `StatusParams` | lines 74–80 |
| `on_tasks` | `TaskStateParams` | lines 82–86 |
| `on_cost_update` | `CostUpdateParams` | lines 181–186 (omitted in research report) |

**Inbound Requests (Python → Rust, id set — Rust must respond):**

| Method | Params type | Response type |
|---|---|---|
| `approval` | `ApprovalRequestParams` | `ApprovalResult` |
| `ask_user` | `AskUserRequestParams` | `AskUserResult` |

**Outbound Requests (Rust → Python, id set — Python responds):**

| Method | Params type | Response type |
|---|---|---|
| `chat` | `ChatParams` | ack |
| `cancel` | `CancelParams` | ack |
| `command` | `CommandParams` | ack |
| `session.new` | `SessionNewParams` | — |
| `session.list` | `SessionListParams` | `SessionListResult` |
| `session.resume` | `SessionResumeParams` | ack with session info |
| `session.fork` | `ForkSessionParams` | `ForkSessionResult` |
| `config.set` | `ConfigSetParams` | — |
| `steer` | `SteerParams` | ack |

### 6.4 Request-Response Correlation

Rust maintains a `pending_requests: HashMap<i64, PendingRequest>` in AppState. When sending a request:

1. Increment `next_request_id`.
2. Insert `(id, PendingRequest { method, sent_at: Instant::now() })`.
3. Send `RPCMessage { jsonrpc: "2.0", id: Some(id), method: Some(method), params: ... }`.

When a response arrives (id set, method absent):

1. Look up `id` in `pending_requests`.
2. Remove the pending entry.
3. Dispatch result to the appropriate handler in the reducer.

Stale requests (no response within 30s): log a warning, remove from pending, surface error_banner.

---

## 7. Go→Rust Port Map (Complete — 30 Files)

| Go source | LOC | Rust target | Notes |
|---|---|---|---|
| `main.go` | ~80 | `src/main.rs` | CLI flags (`--altscreen`), raw-mode RAII guard, tokio runtime init |
| `model.go` | ~300 | `src/state/model.rs` | `AppState` struct; see §3 |
| `view.go` | ~450 | `src/render/view.rs` | Ratatui widget tree; scrollback + live area + status bar + composer |
| `update.go` | ~913 | `src/state/reducer.rs` + `src/event_loop.rs` | Split: pure reducer fn vs tokio event dispatch |
| `commands.go` | ~200 | `src/commands/mod.rs` + `src/commands/*.rs` | One slash-command handler per file |
| `composer.go` | ~200 | `src/ui/composer.rs` | Multi-line input, Alt+Enter, history recall |
| `messages.go` | ~100 | `src/rpc/protocol.rs` | `tea.Msg` → `Event` enum; internal event types |
| `protocol.go` | 187 | `src/rpc/protocol.rs` | All 16 serde structs; semantic/canonical wire parity |
| `backend.go` | ~100 | `src/backend/mod.rs` | Backend lifecycle (start, stop, reconnect) |
| `backend_unix.go` | ~60 | `src/backend/pty.rs` | Linux PTY spawn via portable-pty |
| `backend_windows.go` | ~60 | `src/backend/pty.rs` | ConPTY path (same file; conditional compilation for post-v1) |
| `approval.go` | ~100 | `src/ui/prompts/approval.rs` | Blocking approval modal |
| `askuser.go` | ~100 | `src/ui/prompts/askuser.rs` | Ask-user modal with options + free-text |
| `history.go` | ~150 | `src/history.rs` | Frecency scoring — port verbatim |
| `statusbar.go` | 123 | `src/ui/statusbar.rs` | Model · Provider · Mode · Session · Tokens · Cost · bg |
| `styles.go` | 114 | `src/ui/styles.rs` | Color palette (Tokyo Night) |
| `spinnerverbs.go` | 202 | `src/ui/spinner.rs` | 187 rotating verbs — port verbatim as `const VERBS: [&str; 187]` |
| `detect.go` | ~50 | `src/terminal_detect.rs` | Terminal capability probe |
| `completion.go` | ~120 | `src/ui/completion.rs` | `@path` expansion + fuzzy match |
| `markdown.go` | ~180 | `src/render/markdown.rs` | Inline code/bold/italic/links |
| `taskpanel.go` | ~100 | `src/ui/taskpanel.rs` | `on_tasks` visualization |
| `model_picker.go` | 276 | `src/ui/pickers/model.rs` | Arrow-key + type-to-filter; two-stroke Escape |
| `provider_picker.go` | 185 | `src/ui/pickers/provider.rs` | Same pattern |
| `session_picker.go` | 162 | `src/ui/pickers/session.rs` | Same pattern |
| `milestone_a_test.go` | 1109 | `tests/milestone_a/` | 62 runtime invariant scenarios — port to Rust `#[test]` |
| `model_picker_test.go` | ~200 | `tests/unit/pickers/` | Filter + cursor + Escape tests |
| `provider_picker_test.go` | ~150 | `tests/unit/pickers/` | Same |
| `session_picker_test.go` | ~120 | `tests/unit/pickers/` | Same |
| `palette_test.go` | ~100 | `tests/palette/` | Ctrl+K palette scenarios |
| `*_test.go` (other) | various | `tests/unit/` or `#[cfg(test)]` | Per-module unit tests |

**Deleted at cutover (NOT ported):**
- `autocode/src/autocode/inline/app.py` (+ `renderer.py`, `completer.py`, `__init__.py`) — Python REPL fallback.
- `autocode/src/autocode/tui/commands.py` if it exists purely for the inline path (verify before deletion).

**Retained (test harness, retargets at `$AUTOCODE_TUI_BIN`):**
- `autocode/tests/pty/*.py` — retargets via `$AUTOCODE_TUI_BIN` env var.
- `autocode/tests/tui-comparison/` — retargets via `$AUTOCODE_TUI_BIN`.
- `autocode/tests/tui-references/` — retargets via `$AUTOCODE_TUI_BIN`; all 4 `strict=True` xfails re-evaluated at cutover per Decision (i).
- `autocode/tests/vhs/` — retargets via `$AUTOCODE_TUI_BIN`.

---

## 8. UI Feature Parity (Complete Checklist)

Every visible behavior of the Go TUI must be accounted for before cutover. If a feature is dropped, it gets a decision row added to §1h.1.

### Input and Editing
- [x] **Composer single-line input** — insert characters at cursor, backspace, delete
- [x] **Composer multi-line input** — Alt+Enter inserts newline; display expands upward
- [x] **Cursor movement** — left/right (character), Home/End (line), up/down (line in multi-line)
- [x] **Ctrl+U** — clear line (current line only in multi-line)
- [x] **Ctrl+L** — same as `/clear` (clear scrollback and live area)
- [x] **Frecency history** — up/down arrow recalls previous messages; sorted by last_used+count
- [x] **Enter** — send current composer text as `chat` RPC (only when not streaming)
- [x] **Queue semantics** — messages typed while streaming go to followup queue; sent on `on_done`
- [ ] **`@path` completion** — starts on `@`, fuzzy-matches file paths in current working directory (deferred post-v1)

### Streaming Display
- [x] **Live token display** — `on_token` appended to stream_buf; sliding window rendered
- [x] **Sliding window flush** — when stream_lines exceeds threshold, oldest lines commit to scrollback
- [x] **`on_thinking` display** — dim/separate style from normal tokens
- [x] **`on_done` commit** — remaining stream_buf flushed to scrollback; spinner stops
- [x] **Tool call cards** — `on_tool_call` status updates rendered as distinct cards
- [x] **Scrollback preservation** — inline mode; no `?1049h` unless `--altscreen`

### Status Bar
- [x] **Model · Provider · Mode** — updated on `on_status`
- [x] **Session ID** — truncated display; updated on `on_status` and `session.fork`
- [x] **Token counts** — `tokens_in / tokens_out` updated on `on_done`
- [x] **Cost display** — formatted cost string from `on_cost_update`
- [x] **Background tasks count** — `⏳ N bg` when bg_tasks > 0
- [x] **Plan mode indicator** — `[PLAN]` shown when plan_mode=true

### Spinner
- [x] **Spinner icon** — cycles `⠋⠙⠹⠸` (or equivalent) while streaming
- [x] **194-verb rotation** — verbs rotate every N ticks; exact verb list ported from `spinnerverbs.go`
- [x] **Stops on `on_done`** — spinner clears when streaming ends

### Slash Commands
- [x] **`/` router** — typing `/` starts command typeahead in composer
- [x] **`/clear`** — clears scrollback and live area
- [x] **`/exit`** — graceful shutdown (flush, kill PTY child, restore terminal)
- [x] **`/fork`** → `session.fork` RPC → display new session ID on success
- [x] **`/compact`** → `command {cmd: "/compact"}` RPC
- [x] **`/plan`** → toggles plan_mode; updates status bar
- [x] **`/sessions` / `/resume`** → `session.list` RPC → session picker → `session.resume`
- [x] **`/model`** → model picker
- [x] **`/provider`** → provider picker
- [x] **`/help`** → display available commands

### Ctrl+K Palette
- [x] **Ctrl+K opens palette** — command palette overlay
- [x] **Typeahead filter** — typing narrows visible commands case-insensitively
- [x] **Arrow-key navigation** — up/down moves cursor; Enter selects
- [x] **Escape closes** — restores previous stage

### Pickers (Model / Provider / Session)
- [x] **Arrow-key navigation** — up/down/j/k move cursor
- [x] **Type-to-filter** — typing any printable rune narrows visible entries (case-insensitive)
- [x] **Backspace** — shrinks filter one rune
- [x] **Escape semantics** — first Escape clears filter; second Escape exits picker
- [x] **Enter** — selects from visible (filtered) entries
- [x] **Filter header display** — shows `[filter: cod|]` when filter non-empty
- [x] **Filter reset on exit** — filter cleared when picker dismissed
- [x] **Cursor clamping** — after filter narrows list, cursor stays within visible range

### Ctrl+C Behaviors
- [x] **Idle: Ctrl+C** → send `cancel` RPC, no exit
- [x] **Streaming: first Ctrl+C** → enter steer mode (prompt for mid-stream injection message)
- [x] **Steer mode: Enter** → send `steer {message}` RPC, exit steer mode
- [x] **Steer mode: Escape** → exit steer mode without steering
- [x] **Streaming: second Ctrl+C** → hard cancel (same as `cancel` RPC)
- [x] **Third Ctrl+C** → hard exit regardless of state

### Modals
- [x] **Approval modal** — blocks UI until answered; shows tool name + args; keyboard-only (Y/N/Enter/Escape)
- [x] **Ask-user modal** — options selectable by up/down+Enter; free-text when `allow_text=true`
- [x] **Responses correlated** — `ApprovalResult` / `AskUserResult` sent with matching `id`

### Editor Integration
- [x] **Ctrl+E** — suspend raw mode, spawn `$EDITOR` with current composer text in tempfile
- [x] **Resume after edit** — re-enable raw mode, read tempfile contents into composer
- [x] **Fallback** — if `$EDITOR` unset, display error in banner (do not crash)

### Miscellaneous
- [x] **Resize handling** — terminal resize events propagate to PTY child via `portable-pty`
- [x] **Bracketed paste** — paste events handled without spurious key events
- [x] **Markdown inline rendering** — inline code, bold, italic, hyperlinks
- [x] **Task dashboard** — `on_tasks` → panel showing task list and subagent state
- [x] **`--altscreen` flag** — opt-in; enters `?1049h` on start, leaves on exit
- [x] **Inline mode default** — no `?1049h` unless `--altscreen`; scrollback preserved
- [x] **Unsolicited picker prevention** — picker only opens when explicitly requested (Track 1 invariant)
- [x] **Error banner** — `on_error` displays a dismissable error message
- [ ] **Debug overlay** — Go TUI did not have one; dropped with no decision needed

---

## 9. Testing Strategy

### 9.1 Four Existing Dimensions (All Retarget at `$AUTOCODE_TUI_BIN`)

| Dimension | Current location | Rust retarget path | Policy |
|---|---|---|---|
| **Track 1 — runtime invariants** | `autocode/cmd/autocode-tui/milestone_a_test.go` (62 scenarios, Go test framework) | `autocode/rtui/tests/milestone_a/` (Rust `#[test]` fns) | Port all 62 scenarios; add Rust-only invariants (async task cancellation, tokio channel close-on-error) |
| **Track 4 — design-target ratchet** | `autocode/tests/tui-references/` (Python + live PTY) | `$AUTOCODE_TUI_BIN` → `autocode/rtui/target/release/autocode-tui` | Re-baseline `strict=True` xfails at M11 cutover per Decision (i); document intentional changes |
| **VHS self-regression** | `autocode/tests/vhs/` (pyte + Pillow) | `$AUTOCODE_TUI_BIN` retarget (already env-driven) | VHS baselines regenerated at cutover — user-gated per memory `feedback_vhs_rebaseline_user_gated.md` |
| **PTY smoke** | `autocode/tests/pty/` (pty.fork + select + DSR responder) | `$AUTOCODE_TUI_BIN` retarget | Add new scenario: RPC conformance replay (§6.4) |

### 9.2 New Rust-Native Test Layers

**`cargo test` (unit + integration):**
- Pure reducer tests — `reduce(state, event) == expected_state` with no I/O.
- Serde round-trip tests — every struct in `protocol.rs` serializes and deserializes correctly.
- Spinner tests — 187 verbs present, rotation wraps correctly.
- Picker filter tests — `visibleEntries(all, filter)` is case-insensitive, clamps cursor.
- History frecency tests — recent + frequent entries rank higher.
- Markdown parser tests — inline code/bold/italic rendered correctly.

**JSON-RPC conformance harness (`autocode/rtui/tests/rpc-conformance/`):**
1. Capture Go TUI wire traffic for a set of standard scenarios (stored as `*.jsonl` fixtures).
2. Replay each fixture against the Rust binary via PTY.
3. Compare semantically: same method, id, params/result/error content, same event order.
4. Raw byte-diff is advisory only — JSON field ordering across serializers is not meaningful.
5. Any semantic divergence fails the gate.

**Crossterm render-function tests:**
- Feed `AppState` → call `render_view()` → capture terminal output as a string.
- Assert expected ANSI sequences present (status bar fields, spinner position, etc.).
- No real terminal required — use crossterm's `TestBackend` or write to a `Vec<u8>`.

**Tokio channel stress tests:**
- Backpressure: fill event_tx beyond capacity; assert no panic (use `try_send` + drop).
- Close-on-error: simulate PTY EOF; assert `BackendExit` event arrives and reducer transitions to `Stage::Shutdown`.
- Rapid resize: send 100 Resize events in 1ms; assert PTY resize is called with the final size only.

### 9.3 Artifact Discipline

Every PTY run and every milestone's test suite produces a stored artifact at:
```
autocode/docs/qa/test-results/<YYYYMMDD-HHMMSS>-<label>.md
```
Format: entrypoint, inputs, expected vs observed, pass/fail per check.

---

## 10. Milestone Sequence (M1–M11)

Each milestone must reach its **exit gate** (with a stored artifact) before the next begins. A Codex review gate follows each milestone.

### Rust-M1: Scaffolding, PTY Launch, Minimal RPC, Spike Validation

**Goal:** `autocode-tui` Rust binary spawns `autocode serve` via `portable-pty`, reads `on_status` line, prints it raw, exits on Ctrl+C. Spikes resolve `tui-textarea` and `LinesCodec` questions.

**Key implementation steps:**
1. Create `autocode/rtui/` Cargo project; add to workspace `Cargo.toml`.
2. Add locked baseline crates. Configure `tracing-subscriber` to write to `~/.autocode/tui.log` only.
3. `src/main.rs`: parse `--altscreen` flag, set up raw-mode RAII guard, spawn tokio runtime.
4. `src/backend/pty.rs`: `portable_pty::native_pty_system()` → open PTY → spawn `autocode serve` via `CommandBuilder` (the JSON-RPC backend server, implemented at `autocode/src/autocode/cli.py:371`).
5. PTY reader thread (`spawn_blocking`): read lines → parse `RPCMessage` → send to event channel.
6. Main task: on `RpcNotification("on_status")`, print raw JSON line to stderr (not stdout!) for human inspection.
7. Key reader task: `EventStream` → on `Ctrl+C`, send `Quit` effect → main task kills PTY child and exits.
8. Spike `tui-textarea`: write a test that suppresses all default keybindings and routes Ctrl+K/C/J/U/R to a no-op handler; record verdict.
9. Spike `LinesCodec`: measure max RPC message size from Go wire traces; pick cap or manual splitter.
10. Publish ADR-001 (migration decisions), ADR-002 (async runtime), ADR-003 (ratatui vs raw + tui-textarea verdict).

**Exit gate:**
- `cargo build --release` green; no warnings under `cargo clippy -- -D warnings`.
- PTY artifact: binary starts → `on_status` line received → Ctrl+C exits cleanly → terminal restored.
- Spike verdicts in ADR-002 and ADR-003.
- Post a Codex review request in `AGENTS_CONVERSATION.MD`; get Codex APPROVE before M2.

**Artifact:** `autocode/docs/qa/test-results/<ts>-rust-m1-scaffold.md`

---

### Rust-M2: JSON-RPC Codec + Conformance Harness

**Goal:** All 16 message types round-trip with semantic/canonical parity. Conformance harness against Go wire traces green.

**Key implementation steps:**
1. Complete `src/rpc/protocol.rs` with all 16 serde structs from §6.2.
2. `src/rpc/codec.rs`: `fn encode(msg: &RPCMessage) -> String` and `fn decode(line: &str) -> Result<RPCMessage>`.
3. Unit tests: every struct serializes → deserializes → equals original. Use `serde_json::to_string` + `serde_json::from_str`.
4. `src/rpc/bus.rs`: pending_requests table; request ID counter; dispatch inbound messages to `Event` variants.
5. Capture Go wire traces from `pty_smoke_backend_parity.py` run (stored as `.jsonl` fixture files).
6. Build conformance harness in `tests/rpc-conformance/`: replay fixture → run Rust codec → compare semantically.

**Exit gate:**
- 100+ conformance replay tests green.
- All 16 `#[test]` serde round-trip tests green.
- Codex review → APPROVE before M3.

**Artifact:** `<ts>-rust-m2-rpc-conformance.md`

---

### Rust-M3: Raw Input Loop + Streaming Display

**Goal:** Raw-mode keyboard input; Enter sends `chat`; `on_token` renders with sliding-window flush; `on_done` commits to scrollback.

**Key implementation steps:**
1. Enable raw mode in `main.rs` before spawn.
2. `src/event_loop.rs`: `crossterm::event::EventStream` → `Event::Key` / `Event::Resize`.
3. Reducer: `Stage::Idle + Key(Enter)` → `Effect::SendRpc(chat {...})`.
4. Reducer: `Stage::Idle` → `Stage::Streaming` on `RpcNotification("on_token")`.
5. Renderer: `src/render/view.rs` draws scrollback lines + live stream area.
6. Sliding window: when `stream_lines.len() > N`, oldest lines → `scrollback`.
7. Reducer: `RpcNotification("on_done")` → flush remaining stream to scrollback; `Stage::Streaming` → `Stage::Idle`.
8. Resize: `Event::Resize` → `Effect::ResizePty + Render`.

**Exit gate:**
- PTY smoke: `startup + "hi<Enter>" + streamed response + scrollback preservation` green.
- Reducer unit tests for `on_token` → stage transition and buffer growth.
- Codex review → APPROVE before M4.

**Artifact:** `<ts>-rust-m3-streaming.md`

---

### Rust-M4: Composer (Multi-line, History, Frecency)

**Goal:** Backspace, left/right, Alt+Enter newline, up/down history, frecency sort.

**Key implementation steps:**
1. If `tui-textarea` spike approved: integrate as composer widget.
   If not: `src/ui/composer.rs` with `Vec<char>` line buffer, cursor position, multi-line support.
2. Alt+Enter → insert `\n` in composer; adjust cursor.
3. Up/Down arrow in `Stage::Idle` → history browse; populate composer from `history[cursor]`.
4. On `chat` send: record entry in history with current timestamp; update frecency score.
5. Frecency sort: `score = last_used_ms * 0.7 + use_count * 0.3` (port algorithm from `history.go`).
6. Persist history to `~/.autocode/history.json` (async write on `on_done`).

**Exit gate:**
- Composer unit tests: multi-line, history recall, frecency sort.
- PTY scenario: type 3 messages, press up-arrow, assert first message recalled.
- Codex review → APPROVE before M5.

**Artifact:** `<ts>-rust-m4-composer.md`

---

### Rust-M5: Status Bar + Spinner

**Goal:** Status bar updates on `on_status` / `on_done` / `on_cost_update`; 187-verb spinner on 100ms tick.

**Key implementation steps:**
1. Tick task: `tokio::time::interval(Duration::from_millis(100))` → `Event::Tick`.
2. Reducer: `Event::Tick` → increment `spinner_frame` and `spinner_verb_idx`.
3. `src/ui/statusbar.rs`: renders `Model | Provider | Mode | Session | Tokens | Cost | ⏳ bg`.
4. `src/ui/spinner.rs`: `const VERBS: [&str; 187] = [...]` — port verbatim from `spinnerverbs.go`.
5. `on_status` updates `status.model`, `status.provider`, `status.mode`, `status.session_id`.
6. `on_done` updates `status.tokens_in`, `status.tokens_out`.
7. `on_cost_update` updates `status.cost`.
8. Plan mode: `status_bar` shows `[PLAN]` when `state.plan_mode == true`.

**Exit gate:**
- Track 4 `ready` and `active` scenes reach XPASS or remain xfail with documented pixel-diff rationale.
- Spinner unit test: 187 verbs present, rotation wraps at 187.
- Status bar unit test: all 7 fields rendered correctly.
- Codex review → APPROVE before M6.

**Artifact:** `<ts>-rust-m5-statusbar.md`

---

### Rust-M6: Slash Command Router + Ctrl+K Palette

**Goal:** Core slash commands routed; Ctrl+K opens palette with typeahead.

**Commands to implement:** `/clear /exit /fork /compact /plan /sessions /resume /model /provider /help`

**Key implementation steps:**
1. Composer: `/` prefix detection → command typeahead suggestions.
2. `src/commands/mod.rs`: match command string → dispatch Effect.
3. `/fork` → `Effect::SendRpc(session.fork {...})`.
4. `/plan` → toggle `state.plan_mode`.
5. `/clear` → clear `scrollback` and `stream_buf`.
6. `/exit` → `Effect::Quit`.
7. Ctrl+K → `Stage::Idle` → `Stage::Palette`.
8. `src/ui/palette/mod.rs`: filter-as-you-type; arrow navigation; Enter dispatches command.
9. Palette entries: hardcoded list of all slash commands with descriptions.

**Exit gate:**
- Palette unit tests: filter narrows entries; arrow moves cursor; Escape closes.
- PTY scenario: `/plan` → status bar shows `[PLAN]`; `/plan` again → clears.
- Codex review → APPROVE before M7.

**Artifact:** `<ts>-rust-m6-commands.md`

---

### Rust-M7: Pickers (Model / Provider / Session)

**Goal:** Three picker modals; arrow-key navigation AND type-to-filter; two-stroke Escape; Ctrl+C always exits.

**Picker invariants (per memory `feedback_arrow_key_pickers.md`):**
- Up/down/j/k move cursor through visible (filtered) entries.
- Typing a printable rune appends to filter; narrows visible entries; cursor clamped.
- Backspace shrinks filter.
- First Escape: clear filter (if non-empty). Second Escape: exit picker.
- Enter: select from visible entries; send appropriate RPC.
- Filter header: `Select a model: [filter: cod|]` when filter non-empty.
- Filter reset to empty string when picker is dismissed.

**Key implementation steps:**
1. `src/ui/pickers/mod.rs`: `PickerState`, `fn visible_entries(all: &[String], filter: &str) -> Vec<usize>` (case-insensitive `contains`).
2. Reducer: picker-specific key handling for the three pickers (share logic via `PickerKind` dispatch).
3. `/model` → populate picker with entries from last `on_status` or a new `config.set` request.
4. `/provider` → same pattern.
5. `/sessions` → `session.list` RPC → populate session picker; on select → `session.resume`.
6. On picker exit (Escape or Enter): `state.picker = None`; restore previous stage.

**Exit gate:**
- Per-picker unit tests mirror `model_picker_test.go`: filter narrows, cursor clamps, Escape clears then exits, Enter selects.
- PTY scenario: `/model` → type `cod` → only matching entries visible → Enter selects.
- `pty_tui_bugfind.py` finds 0 picker-related bugs.
- Codex review → APPROVE before M8.

**Artifact:** `<ts>-rust-m7-pickers.md`

---

### Rust-M8: Approval / Ask-User / Steer / Fork

**Goal:** Approval modal blocks tool execution until answered; ask-user supports options + free-text; first Ctrl+C mid-stream → steer prompt; `/fork` exchanges params → result.

**Key implementation steps:**
1. `src/ui/prompts/approval.rs`: blocking overlay; Y/N keybindings; Enter confirms; Escape denies.
2. On `RpcInboundRequest("approval")`: transition to `Stage::Approval`, save `rpc_id`.
3. On approval answer: `Effect::SendRpc(RPCResponse { id: rpc_id, result: ApprovalResult {...} })`.
4. `src/ui/prompts/askuser.rs`: options list with arrow navigation; free-text fallback; Enter confirms.
5. On `RpcInboundRequest("ask_user")`: transition to `Stage::AskUser`.
6. Steer mode: `Stage::Streaming + Key(Ctrl+C)` (first press) → `Stage::AskUser` (repurposed for steer prompt, or dedicated stage); on Enter → `Effect::SendRpc(steer {...})`.
7. `/fork` → `session.fork` RPC → on `ForkSessionResult` → update `status.session_id`, display confirmation.
8. `pty_smoke_backend_parity.py` green: steer + fork scenarios.

**Exit gate:**
- Approval modal unit test: Y → approved=true; Escape → approved=false; rpc_id correlates.
- Backend-parity PTY smoke green.
- Codex review → APPROVE before M9.

**Artifact:** `<ts>-rust-m8-approval-steer-fork.md`

---

### Rust-M9: Editor / Plan Mode / Task Panel / Followup Queue / Markdown

**Goal:** Full feature parity. All remaining behavioral checklist items from §8 closed.

**Key implementation steps:**
1. **Editor launch** (`Ctrl+E`): `Effect::SetRawMode(false)` → `Effect::SpawnEditor(composer_text)` → main task runs editor blocking → `Effect::SetRawMode(true)` → `Event::EditorDone(contents)`.
2. **Followup queue**: on `on_done` with `followup_queue` non-empty, pop and send next `chat` automatically.
3. **Task panel** (`src/ui/taskpanel.rs`): `on_tasks` → renders task list with status indicators and subagent entries.
4. **Markdown renderer** (`src/render/markdown.rs`): scan for `` `code` ``, `**bold**`, `*italic*`, `[link](url)`; apply crossterm styling.
5. **Bracketed paste**: `enable_bracketed_paste()` on startup; handle `Event::Paste(text)` → insert into composer.
6. Full Track 4 scene suite: all `ready/active/narrow/recovery` scenes + 10 stubbed scenes populated.
7. VHS scenes green against rebaselined PNGs (user-gated rebaseline).

**Exit gate:**
- All UI parity checklist items from §8 checked.
- Full Track 4 suite (including previously-stubbed scenes) green or documented xfail.
- VHS regression green (after user approves rebaseline).
- Codex review → APPROVE before M10.

**Artifact:** `<ts>-rust-m9-final-features.md`

---

### Rust-M10: Linux Release Hardening + Performance Gate

**Goal:** Production-quality Linux binary. Performance targets met. Docs published.

**Performance targets:**

| Metric | Target | Measurement method |
|---|---|---|
| First-token render latency | <50ms after `on_token` arrival | Timestamped log + PTY artifact |
| Keystroke-to-render | <16ms (1 frame @60Hz) | Synthetic key injection in conformance harness |
| Idle CPU | <1% | `top -p $(pidof autocode-tui)` sampling |
| Memory footprint | <50MB RSS | `/proc/self/status` sampling |
| Scrollback ring | Bounded to 10,000 lines | Ring buffer assertion in unit tests |
| Startup time | <200ms cold | `time autocode-tui --version` (excludes Python backend spawn) |
| Binary size | <10MB stripped | `ls -lh target/release/autocode-tui` |

**Key implementation steps:**
1. `cargo build --release` with `lto = "thin"` and `strip = true`.
2. Run `cargo clippy -- -D warnings` clean.
3. Measure all perf targets; fix any that miss.
4. Full 23-lane benchmark regression with Rust binary (`$AUTOCODE_TUI_BIN` pointed at Rust binary).
5. Publish `docs/reference/rust-tui-architecture.md`.
6. Publish `docs/reference/rust-tui-rpc-contract.md`.
7. Update `autocode/tests/tui-comparison/README.md` and `autocode/tests/tui-references/README.md` with binary retargeting notes.
8. Linux CI (GitHub Actions) green.

**Exit gate:**
- All perf targets met; measurement artifact stored.
- Full 23-lane benchmark green.
- Reference docs published.
- CI green.
- Codex + user review → APPROVE before M11.

**Artifact:** `<ts>-rust-m10-release-gate.md`

---

### Rust-M11: Cutover (Delete Go TUI + Python Inline)

**Goal:** Remove Go TUI and Python inline fallback. Rust binary is the sole frontend.

**Key implementation steps:**
1. Delete `autocode/cmd/autocode-tui/` from the working tree (builder deletes the files; user commits — agents do NOT run `git rm` or any tree-mutating git command per `AGENTS.md:19`).
2. Delete `autocode/src/autocode/inline/app.py`, `renderer.py`, `completer.py`, `__init__.py` from the working tree.
3. Verify `autocode/src/autocode/tui/commands.py` — delete from working tree if only used by inline path.
4. Update `CLAUDE.md` and `AGENTS.md` — remove all Go TUI references.
5. Update `docs/session-onramp.md` — remove inline fallback instructions.
6. Update `autocode/TESTING.md` — reflect Rust test commands.
7. Update `Makefile` — remove `go build` targets; add `cargo build --release`.
8. Re-evaluate all Track 4 `strict=True` xfail decorators — remove where Rust passes; keep where genuine gap.
9. Final PTY smoke + conformance harness run → stored artifact.
10. User-authored commit (per commit policy — Claude/Codex never commit).

**Exit gate:**
- User-authored commit.
- Release note published citing complete validation matrix.
- No Go or Python inline references in non-archive docs.
- All 4 testing dimensions green against Rust binary.

**Artifact:** `<ts>-rust-m11-cutover.md`

---

## 11. Performance and Platform

### 11.1 Performance Targets (Summary)

See §10 (Rust-M10) for measurement methods.

| Metric | Target |
|---|---|
| First-token render | <50ms |
| Keystroke-to-render | <16ms |
| Idle CPU | <1% |
| Memory footprint | <50MB RSS |
| Scrollback bound | 10,000 lines |
| Startup time | <200ms (cold, excluding Python) |
| Binary size | <10MB stripped |

### 11.2 Platform Matrix

| Platform | Status | Notes |
|---|---|---|
| Linux x86_64 | REQUIRED for v1 | xterm, Ghostty, kitty, alacritty, gnome-terminal, tmux |
| macOS | NEVER | Out of scope for all versions of this product |
| Windows x86_64 | post-v1 | Architecture stays ConPTY-capable; no Windows CI until Windows work begins |

---

## 12. Risk Register

| ID | Severity | Risk | Mitigation |
|---|---|---|---|
| R1 | HIGH | PTY framing differences cause RPC deadlocks on Windows ConPTY | Post-v1 Windows; conformance harness required before enabling |
| R2 | HIGH | Ratatui ecosystem less mature for complex TUI overlays (pickers, palette) | M7 picker slice has explicit spike budget; ratatui vendoring allowed if upstream blocks |
| R3 | MED | Async Rust + blocking PTY I/O is a known footgun (see §4.3) | Dedicated `spawn_blocking` per stream; tokio `mpsc` channels for internal dispatch; ADR records decision |
| R4 | MED | Pixel-for-pixel parity constraint freezes UX improvements | Decision (i): permission to improve; Track 4 re-baseline at cutover |
| R5 | MED | Migration freezes §1f Milestones C/D/E/F | Decision (d): Go gates stopped; absorbed into Rust-M5–M10 |
| R6 | MED | Contributor onboarding requires Rust toolchain | `autocode/rtui/README.md` documents `rustup install stable`, `cargo build`, platform deps |
| R7 | LOW | Claude/Codex have less Rust review context than Go | Reviewer prompts updated with Rust idiom references |
| R8 | LOW | Go TUI frozen while Rust speculative — known gaps stay open | Accepted schedule bet per Decision (d); fatal blocker = user decides whether to abandon §1h |
| R9 | LOW | Binary size >10MB | `strip = true`, `lto = "thin"`, minimal dep profile; target documented in M10 |
| R10 | MED | `tui-textarea` default keybindings collide with app controls (Ctrl+K, Ctrl+C, Ctrl+J, Ctrl+U, Ctrl+R) | M1 spike proves full override possible; if not, hand-roll composer (~100 LOC) |
| R11 | MED | `crossterm` semver skew: ratatui + direct dep resolve different versions, splitting raw-mode state | Pin crossterm to ratatui's exact required range from day one; verify with `cargo tree \| grep crossterm` |

---

## 13. Documentation Deliverables

Created or updated as part of the migration:

| Document | Milestone | Description |
|---|---|---|
| `docs/decisions/ADR-001-rust-tui-migration.md` | M1 | Decisions (a)–(l) with rationale |
| `docs/decisions/ADR-002-rust-async-runtime.md` | M1 | Tokio vs async-std; PTY threading approach |
| `docs/decisions/ADR-003-ratatui-vs-raw-crossterm.md` | M1 | Layering choice; tui-textarea verdict |
| `autocode/rtui/README.md` | M1 | Build, run, contributor setup (`rustup`, `cargo build --release`) |
| `docs/reference/rust-tui-architecture.md` | M1 | Architecture overview for reviewers |
| `docs/reference/rust-tui-rpc-contract.md` | M2 | Frozen JSON-RPC spec (all 16 types) |
| `autocode/tests/tui-comparison/README.md` | M3 | Note: `$AUTOCODE_TUI_BIN` retargets Rust binary |
| `autocode/tests/tui-references/README.md` | M3 | Rust cutover re-baseline policy |
| `docs/tests/tui-testing-strategy.md` | M3 | Update Rust binary resolution path |
| `CLAUDE.md` + `AGENTS.md` | **M11 only** | Frontend language reference (do NOT update before cutover) |
| `docs/session-onramp.md` | M11 | Remove inline fallback; add Rust contributor flow |

---

## 14. Explicit Non-Goals

- Changing the JSON-RPC protocol (even additive changes — separate plan).
- Changing the Python backend surface.
- Retiring hooks, skills, or rules loader.
- Parity with non-autocode TUIs (claude-code / opencode / codex / aider) beyond existing Track 4 research.
- Remote-client architecture.
- New agent behavior on the backend.
- macOS support in any version.
- Windows support before v1 is shipped.

---

## 15. Reviewer Protocol

The build sequence is strictly linear. Each milestone requires Codex APPROVE before the next begins:

1. User approves decisions (a)–(l) — **DONE** (Entry 1220).
2. Codex architecture review — **DONE** (Entry 1229 APPROVE).
3. User assigns Rust-M1 builder — **PENDING**.
4. Rust-M1 → ADR-001/002/003 → Codex APPROVE.
5. Rust-M2 → conformance harness → Codex APPROVE (highest-risk semantic parity gate).
6. Rust-M3 through M9 → per-milestone PTY artifact → Codex APPROVE.
7. Rust-M10 → performance + CI → Codex + user APPROVE.
8. Full 23-lane benchmark regression with Rust binary green.
9. Rust-M11 cutover → user-authored commit (Claude/Codex do not commit).
