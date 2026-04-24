# AutoCode Feature Behavior Inventory

> Current-state inventory for modularization work.
> Purpose: describe what the frontend owns, what the backend owns, how they talk, and what currently prevents easy UI/backend swapping.
> Last updated: 2026-04-24

This file is intentionally about the runtime as it exists today, not the historical catalog in `docs/requirements_and_features.md`. Use this as the baseline for splitting AutoCode into independently runnable and testable modules.

## 1. Runtime Decomposition

| Module | Current implementation | Primary entrypoint | Individually runnable today? | Individually testable today? |
|---|---|---|---|---|
| Launcher | Python CLI | `autocode` / `autocode chat` in `autocode/src/autocode/cli.py` | Yes | Yes |
| Frontend | Rust TUI | `autocode/rtui/target/release/autocode-tui` | Yes, in either spawn-managed or `--attach HOST:PORT` mode | Yes |
| Backend | Python JSON-RPC server | `autocode serve` in `autocode/src/autocode/cli.py` | Yes, over stdio or TCP JSON-RPC | Yes |
| Shared contract | JSON-RPC v1 schema | `docs/reference/rpc-schema-v1.md`, `autocode/src/autocode/backend/schema.py`, `autocode/rtui/src/rpc/protocol.rs` | N/A | Yes |

## 2. Launcher Inventory

The launcher is not the product surface the user asked to modularize, but it is the bridge that currently ties frontend and backend together.

Current behavior:

- Bare `autocode` launches the Rust TUI by default.
- `autocode chat --mode inline|altscreen` selects frontend presentation mode.
- Bare `autocode --attach HOST:PORT` launches the Rust TUI in attach mode against an already-running backend host.
- `autocode serve --transport stdio|tcp` launches the backend server as a JSON-RPC process.
- `autocode ask` runs a one-shot LLM call without the TUI/backend split.
- `autocode chat --tui` still exposes the older Textual fallback.
- `autocode chat --legacy` still exposes the older Rich REPL fallback.

Current ownership:

- Binary discovery for the Rust UI lives in `autocode/src/autocode/cli.py`.
- Session resume handoff into the Rust UI currently happens through `AUTOCODE_SESSION_ID`.
- Backend launch discovery for the Rust UI currently happens through `AUTOCODE_PYTHON_CMD`.
- Attach-mode handoff into the Rust UI currently happens through `--attach HOST:PORT` or `AUTOCODE_BACKEND_ADDR`.

Modularization implication:

- The CLI is currently both a launcher and a policy layer.
- A clean split will likely want a narrower launcher contract so frontend and backend can be composed without the CLI deciding process topology.

## 3. Frontend Inventory

### 3.1 Canonical frontend

The canonical interactive frontend is the Rust TUI in `autocode/rtui/`.

Primary files:

- `autocode/rtui/src/main.rs`
- `autocode/rtui/src/state/model.rs`
- `autocode/rtui/src/state/reducer.rs`
- `autocode/rtui/src/render/view.rs`
- `autocode/rtui/src/rpc/`
- `autocode/rtui/src/backend/connection.rs`
- `autocode/rtui/src/backend/pty.rs`

### 3.2 Frontend-owned behavior

The Rust frontend currently owns:

- terminal lifecycle
- raw-mode entry and cleanup
- inline vs alt-screen presentation
- composer editing and multiline input
- history navigation and frecency
- local scrollback and streamed-line assembly
- spinner and working/streaming/idle/recovery stage transitions
- local recovery UI for stale requests and backend failures
- palette and slash-autocomplete UX
- picker UX for sessions and other backend-provided lists
- approval and ask-user modal UX
- local task/subagent panel rendering
- detail surfaces and followup queue rendering
- keyboard shortcuts, paste handling, resize handling, and editor round-trip

In practical terms, the frontend is responsible for how interaction feels on screen, even when the data itself is backend-owned.

### 3.3 Frontend inputs and outputs

Frontend -> backend requests currently include:

- `chat`
- `cancel`
- `command`
- `command.list`
- `session.new`
- `session.list`
- `session.resume`
- `model.list`
- `provider.list`
- `task.list`
- `subagent.list`
- `subagent.cancel`
- `plan.status`
- `plan.set`
- `config.get`
- `config.set`
- `memory.list`
- `checkpoint.list`
- `checkpoint.restore`
- `plan.export`
- `plan.sync`
- `steer`
- `session.fork`
- `shutdown`

Backend -> frontend notifications currently drive:

- status/footer state via `on_status`
- retry/degraded-upstream visibility via `on_warning`
- streamed output via `on_token`
- thinking output via `on_thinking`
- turn completion via `on_done`
- tool activity via `on_tool_call`
- task/subagent side-panel data via `on_task_state`
- cost/token counters via `on_cost_update`
- visible failures via `on_error`
- request liveness via `on_chat_ack`

Backend -> frontend requests currently drive:

- approvals via `on_tool_request`
- explicit user questions via `on_ask_user`

### 3.4 Frontend-local state that is not backend-owned

The frontend maintains local-only state for:

- current stage and recovery mode
- scroll offset
- spinner frames
- composer buffer
- palette filter and cursor
- picker filter and cursor
- modal queue
- stale pending-request detection
- followup queue
- current visual error banner
- history ranking

This state is UI-specific and should stay frontend-owned after modularization.

### 3.5 Frontend run and test surfaces

Run:

```bash
cd autocode/rtui && cargo build --release
./target/release/autocode-tui
./target/release/autocode-tui --altscreen
./target/release/autocode-tui --attach 127.0.0.1:8765
autocode --attach 127.0.0.1:8765
```

Test:

```bash
cd autocode/rtui && cargo test
cd autocode/rtui && cargo clippy -- -D warnings
cd autocode/rtui && cargo fmt -- --check
python3 autocode/tests/pty/pty_smoke_rust_m1.py
python3 autocode/tests/pty/pty_smoke_rust_comprehensive.py
python3 autocode/tests/pty/pty_e2e_real_gateway.py
make tui-regression
make tui-references
uv run python autocode/tests/vhs/run_visual_suite.py
```

### 3.6 Frontend replaceability status

What is already good:

- most visual state is isolated in reducer + renderer layers
- the Rust TUI speaks a documented RPC contract
- the Rust TUI can either spawn-manage a backend or attach to a running TCP backend
- there is already strong frontend-focused test coverage

What still blocks easy UI swapping:

- the default product path still bundles launcher policy with a spawn-managed backend topology
- spawn-managed mode is a stdio subprocess path, while attach mode is TCP; capability negotiation across those modes is still implicit
- some UX semantics depend on backend-owned slash command definitions and backend-owned picker data
- some behavior contracts exist only as implementation behavior, not as explicit protocol guarantees

## 4. Backend Inventory

### 4.1 Canonical backend

The backend is the Python JSON-RPC application in `autocode/src/autocode/backend/server.py` plus its host adapters.

Primary files:

- `autocode/src/autocode/backend/server.py`
- `autocode/src/autocode/backend/chat.py`
- `autocode/src/autocode/backend/services.py`
- `autocode/src/autocode/backend/dispatcher.py`
- `autocode/src/autocode/backend/schema.py`
- `autocode/src/autocode/backend/stdio_host.py`
- `autocode/src/autocode/backend/tcp_host.py`
- `autocode/src/autocode/agent/loop.py`
- `autocode/src/autocode/app/commands.py`
- `autocode/src/autocode/agent/tools.py`
- `autocode/src/autocode/agent/task_tools.py`
- `autocode/src/autocode/agent/subagent_tools.py`
- `autocode/src/autocode/session/`

### 4.2 Backend-owned behavior

The backend currently owns:

- session creation, listing, resume, and fork
- persistent message and tool-call storage
- model/provider/config state
- approval policy and tool approval decisions
- ask-user request generation
- task and subagent orchestration
- memory store and checkpoint store
- plan mode state and plan artifact export/sync
- chat routing across Layer 1, Layer 2, Layer 3, and Layer 4
- provider creation and actual model calls
- tool registry creation and tool execution
- project memory loading and prompt assembly
- event recording, session logging, and training-data capture

The backend is the system of record for durable session/task/subagent state. The frontend only renders projections of that state.

### 4.3 Backend APIs currently exposed to a frontend

The backend exposes two host shapes today:

- newline-delimited JSON-RPC 2.0 over stdin/stdout
- newline-delimited JSON-RPC 2.0 over TCP

That service currently supports:

- chat turns and cancellation
- slash-command execution
- backend-owned command discovery
- session lifecycle
- provider/model discovery
- plan/memory/checkpoint listing and mutation
- steering an active run
- backend-triggered approval and ask-user flows

### 4.4 Backend-internal domains currently mixed together

The backend stack is currently still a broad application surface, even after transport extraction. It is currently both:

- an application-service layer
- an orchestration entrypoint
- a session/task/subagent state manager
- a slash-command runtime host

Transport ownership itself is now split out into `stdio_host.py` and `tcp_host.py`.

That makes it powerful, but it also means the backend module boundary is not yet cleanly separated internally.

### 4.5 Backend run and test surfaces

Run:

```bash
autocode serve --transport stdio
autocode serve --transport tcp --host 127.0.0.1 --port 8765
```

Direct programmatic exercise:

- instantiate `BackendServer` and call handlers in Python tests

Test:

```bash
uv run pytest autocode/tests/unit/test_backend_server.py -v
uv run pytest autocode/tests/unit/test_backend_chat.py -v
uv run pytest autocode/tests/unit/test_backend_transport_conformance.py -v
uv run pytest autocode/tests/unit/test_cli.py -v
uv run pytest -m integration autocode/tests/integration/ -v
uv run python benchmarks/benchmark_runner.py --agent autocode --autocode-runner tui --lane B7 --model swebench --max-tasks 1
```

### 4.6 Backend replaceability status

What is already good:

- there is a documented RPC surface
- the backend can run headless without the Rust UI
- the backend can be hosted over stdio or TCP
- much of the backend can be exercised directly in Python unit tests

What still blocks easy backend swapping:

- the frontend assumes the current JSON-RPC method set and the current spawn-managed or attach-mode startup model
- the backend application surface is still centered on `BackendServer`, with `chat.py` depending on a wide host protocol rather than a thinner service boundary
- transport abstraction exists, but only stdio and single-client TCP hosts are built today
- capability negotiation, reconnect, and remote-host security semantics are still not explicit

## 5. Shared Contract Inventory

The current stable seam is the RPC schema v1 contract.

Source-of-truth files:

- `docs/reference/rpc-schema-v1.md`
- `autocode/src/autocode/backend/schema.py`
- `autocode/rtui/src/rpc/protocol.rs`
- `autocode/rtui/src/rpc/schema.rs`

This contract currently defines:

- canonical method names
- payload shape for requests, notifications, and responses
- startup status expectations
- tool approval and ask-user request/response round-trips
- task/subagent projection shape

The contract does not yet fully define:

- transport negotiation across the current stdio/TCP hosts or future transports
- capability negotiation between frontend and backend
- protocol version negotiation
- reconnect/reattach semantics
- out-of-process remote frontend attachment

## 6. Current Coupling Seams

These are the main places where frontend and backend are not yet cleanly swappable.

### 6.1 Process topology is still bundled into the default product path

The Rust TUI now supports both spawn-managed and attach mode, but the default bare-`autocode` experience still bundles launcher policy and frontend/backend topology together.

### 6.2 Slash command semantics are shared, but still backend-led

The old `autocode.tui.commands` leak is fixed: command semantics now live in `autocode.app.commands`. The remaining seam is that frontend UX still depends on the backend-owned command catalog and backend-owned provider/model/session list data.

### 6.3 Transport is abstracted, but not broadly generalized

The same business behavior now works over local stdio JSON-RPC and TCP JSON-RPC, but not yet over:

- local socket
- WebSocket
- in-process API

### 6.4 Backend service boundaries are broad

`BackendServer` currently owns transport, orchestration, session lifecycle, approvals, plan state, memory/checkpoint access, and command runtime. A future swap-friendly backend should likely expose a thinner service boundary.

### 6.5 Some frontend behaviors are driven by implementation detail instead of explicit contract

Examples:

- stale-request timeout semantics
- when chat-ack heartbeats are required
- which request types imply visible progress
- which session transitions must clear local frontend state

These should become explicit contract rules or conformance tests.

## 7. Individually Runnable and Testable Status

Today:

- the frontend is individually runnable in either spawn-managed or attach mode
- the backend is individually runnable over stdio or TCP
- both sides are individually testable
- the RPC boundary is testable and documented

This means AutoCode is partially modular today:

- test modularity: mostly yes
- runtime modularity: partly
- swap-in-any-UI: not yet
- swap-in-any-backend: not yet

## 8. Recommended Next Separation Seams

This is not the full execution plan. It is the minimum set of seams the inventory says should be isolated next.

1. Extract a backend-agnostic application service layer from `BackendServer`.
2. Move slash-command definitions and provider/model discovery out of `autocode.tui.commands` into a shared application module.
3. Introduce a transport abstraction so the backend can run over stdio first, but not only stdio.
4. Split the Rust frontend's backend process spawning from its RPC client responsibilities.
5. Convert current behavior assumptions such as `on_chat_ack`, stale-timeout rules, and session-reset semantics into explicit conformance tests at the contract boundary.

## 9. Modularization Readiness Summary

The cleanest modular boundary that already exists is:

- frontend: render/input/state
- backend: orchestration/domain state
- contract: RPC schema v1

The main reasons swapping is still hard are:

- startup topology is still bundled into the default launcher/frontend path
- command catalog and picker flows are still backend-led UX seams
- transport abstraction is present, but capability/reconnect/security semantics are still incomplete
- backend server responsibilities are too wide

That means the next modularization phase should focus first on interface extraction and process-boundary cleanup, not on rewriting the TUI or the agent loop.
