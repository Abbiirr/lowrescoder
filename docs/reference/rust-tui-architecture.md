# Rust TUI Architecture

## Overview

The AutoCode Rust TUI (`autocode-tui`) replaces the Go BubbleTea TUI with a Rust implementation using `crossterm` + `ratatui` + `tokio`. It communicates with the Python backend via newline-delimited JSON-RPC over either a spawn-managed stdio subprocess or a localhost TCP attach connection.

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
│  RPC reader│(spawn_blocking)         │RPC writer             │
│  (blocking │ Read)                   │(blocking Write)       │
│            ▼                         ▼                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │   Backend connection (stdio subprocess or TCP attach)│   │
│  └────────────────────────┬─────────────────────────────┘   │
└───────────────────────────┼────────────────────────────────┘
                            │ framed JSON, 1 msg/line, LF
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Python backend                                               │
│  autocode/src/autocode/backend/server.py + host adapters      │
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
│   └── bus.rs                 # backend reader/writer tasks, request correlation
├── backend/
│   ├── connection.rs          # spawn-managed vs attach/TCP backend selection
│   ├── stdio.rs               # spawn-managed stdio subprocess + stderr log pipe
│   └── process.rs             # child lifecycle monitor + exit status
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
2. **The Rust process owns terminal raw mode.** The Python backend is not terminal-interactive; it speaks JSON-RPC over stdio or TCP.
3. **The state machine is a pure reducer** — `fn reduce(state: AppState, event: Event) -> (AppState, Vec<Effect>)` — testable without a terminal or network.
4. **Rendering is pull-based from state** — no render calls from inside the input router, RPC decoder, or backend monitor tasks.
5. **Backend I/O is blocking at the handle seam; tokio channels are async.** Reader/writer handles live behind the RPC bus and communicate with the main task over channels.

## Async Architecture

Five concurrent units of execution:

| Unit | Type | Owns | Reads from | Writes to |
|---|---|---|---|---|
| Main task | `tokio::task` | `AppState`, ratatui terminal | `event_rx` | `rpc_tx`, terminal |
| Key reader | `tokio::task` | `crossterm::event::EventStream` | Terminal stdin | `event_tx` |
| RPC reader | `spawn_blocking` | backend `Read` handle | stdio/TCP backend connection | `event_tx` |
| RPC writer | `spawn_blocking` | backend `Write` handle | `rpc_rx` | stdio/TCP backend connection |
| Tick task | `tokio::task` | `tokio::time::interval` | Timer | `event_tx` |

## State Machine

### AppState

Top-level state with: scrollback (bounded 10k lines), streaming buffers, composer, history, status bar, spinner, pickers, palette, approval/ask-user modals, followup queue, task panel, error banner, plan mode flag, terminal geometry, and RPC correlation table.

### Stage Enum

`Idle | Streaming | ToolCall | Approval | AskUser | Picker(kind) | Palette | EditorLaunch | Shutdown`

### Event Enum

`Key | Resize | Tick | RpcNotification | RpcResponse | RpcInboundRequest | BackendExit | BackendError | EditorDone`

### Effect Enum

`SendRpc | Render | SpawnEditor | Quit`

## Crate Stack

| Crate | Version | Purpose |
|---|---|---|
| `crossterm` | 0.28 | Terminal I/O, raw mode, EventStream |
| `ratatui` | 0.29 | Layout + widgets |
| `tokio` | 1 (full) | Async runtime |
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
