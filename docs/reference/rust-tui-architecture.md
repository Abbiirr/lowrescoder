# Rust TUI Architecture

## Overview

The AutoCode Rust TUI (`autocode-tui`) replaces the Go BubbleTea TUI with a Rust implementation using `crossterm` + `ratatui` + `tokio` + `portable-pty`. It communicates with the unchanged Python backend via JSON-RPC over a PTY.

## System Diagram

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
└─────────────────────────────────────────────────────────────┘
```

## Module Layout

```
autocode/rtui/src/
├── main.rs                    # CLI args, raw-mode RAII guard, tokio runtime
├── state/
│   ├── model.rs               # AppState struct
│   ├── reducer.rs             # pure reduce() fn
│   └── reducer_tests.rs       # 14 unit tests
├── rpc/
│   ├── protocol.rs            # 16 serde structs + round-trip tests
│   ├── codec.rs               # line encode/decode, LF framing
│   └── bus.rs                 # PTY reader/writer tasks, request correlation
├── backend/
│   ├── pty.rs                 # portable-pty spawn
│   └── process.rs             # child lifecycle monitor
├── ui/
│   ├── composer.rs            # multi-line input, history
│   ├── spinner.rs             # 194-verb spinner
│   ├── history.rs             # frecency scoring, persistence
│   ├── event_loop.rs          # crossterm EventStream → event_tx
│   ├── palette/               # Ctrl+K command palette
│   └── pickers/               # model/provider/session pickers
├── render/
│   ├── view.rs                # ratatui widget tree
│   └── markdown.rs            # inline code/bold/italic/links
└── commands/                  # slash command router
```

## Key Architectural Invariants

1. **The RPC wire format is frozen.** Rust must be semantically indistinguishable on the wire.
2. **The Rust process owns stdin/stdout raw mode.** Python child runs inside a PTY.
3. **The state machine is a pure reducer** — `fn reduce(state: AppState, event: Event) -> (AppState, Vec<Effect>)` — testable without a terminal or network.
4. **Rendering is pull-based from state** — no render calls from inside the input router, RPC decoder, or PTY monitor tasks.
5. **PTY I/O is blocking; tokio channels are async.** `portable-pty`'s handles MUST live in `spawn_blocking` threads.

## Async Architecture

Five concurrent units of execution:

| Unit | Type | Owns | Reads from | Writes to |
|---|---|---|---|---|
| Main task | `tokio::task` | `AppState`, ratatui terminal | `event_rx` | `rpc_tx`, terminal |
| Key reader | `tokio::task` | `crossterm::event::EventStream` | Terminal stdin | `event_tx` |
| PTY reader | `spawn_blocking` | PTY master `Read` handle | PTY master | `event_tx` |
| PTY writer | `spawn_blocking` | PTY master `Write` handle | `rpc_rx` | PTY master |
| Tick task | `tokio::task` | `tokio::time::interval` | Timer | `event_tx` |

## State Machine

### AppState

Top-level state with: scrollback (bounded 10k lines), streaming buffers, composer, history, status bar, spinner, pickers, palette, approval/ask-user modals, followup queue, task panel, error banner, plan mode flag, terminal geometry, and RPC correlation table.

### Stage Enum

`Idle | Streaming | ToolCall | Approval | AskUser | Picker(kind) | Palette | EditorLaunch | Shutdown`

### Event Enum

`Key | Resize | Tick | RpcNotification | RpcResponse | RpcInboundRequest | BackendExit | BackendError | EditorDone`

### Effect Enum

`SendRpc | Render | SetRawMode | ResizePty | EnterAltScreen | LeaveAltScreen | SpawnEditor | Quit`

## Crate Stack

| Crate | Version | Purpose |
|---|---|---|
| `crossterm` | 0.28 | Terminal I/O, raw mode, EventStream |
| `ratatui` | 0.29 | Layout + widgets |
| `tokio` | 1 (full) | Async runtime |
| `portable-pty` | 0.8 | PTY spawn |
| `serde` + `serde_json` | 1 | JSON codec |
| `anyhow` | 1 | Error propagation |
| `tracing` + `tracing-subscriber` | 0.1/0.3 | File-only logging |

## Performance Profile

| Metric | Target | Observed |
|---|---|---|
| Binary size | <10MB | 2.4MB |
| Startup time | <200ms | 2ms |
| Idle CPU | <1% | ~0% |
| Memory | <50MB | ~15MB |

## Build

```bash
cd autocode/rtui
cargo build --release
# Binary: target/release/autocode-tui
```
