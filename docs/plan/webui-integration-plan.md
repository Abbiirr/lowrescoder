# WebUI Integration Plan — AutoCode IDE GUI ↔ Backend Harness

Status: v1.0 — 2026-07-03 · Author: Claude (architect) · Implementers: Opus subagents
Prototype: `ui-designs/AutoCode.html` (implements Claude Design `AutoCode.dc.html`)
Coverage analysis: `ui-designs/harness-coverage.md`

## 1. Goal

Turn the static IDE GUI prototype into a real frontend for the AutoCode harness: a
browser client speaking the backend's documented JSON-RPC protocol over WebSocket,
with a protocol-conformant mock server for development/verification, and a drop-in
WS host adapter for the real backend. The GUI is a **second frontend** beside the
canonical Rust TUI — same backend, same events, different surface.

## 2. Ground truth

### 2.1 Documented protocol (from `docs/features/agent-events.md`, `docs/features/backend_features.md`)

Frontend-facing **request methods** (client → server):
`chat`, `cancel`, `command`, `command.list`, `session.new`, `session.list`,
`session.resume`, `session.fork`, `model.list`, `provider.list`, `task.list`,
`subagent.list`, `subagent.cancel`, `plan.status`, `plan.set`, `plan.export`,
`plan.sync`, `config.get`, `config.set`, `memory.list`, `checkpoint.list`,
`checkpoint.restore`, `steer`, `shutdown`.

**Notifications** (server → client): `on_token`, `on_thinking`, `on_tool_call`,
`on_done`, `on_status`, `on_error`, `on_warning`, `on_cost_update`, `on_task_state`,
`on_chat_ack`, `on_tool_request`, `on_ask_user`.

**Approval flow**: `on_tool_request` / `on_ask_user` are server-initiated JSON-RPC
*requests* (the host has `route_rpc_response`); the client replies with a JSON-RPC
*response* carrying the decision. (Verify against `rpc-schema-v1` fixtures when the
source checkout is available — flagged as open question.)

**Event contract** (agent-events.md): every notification maps to a typed `AgentEvent`
(`BaseEvent`: `id`, `sessionId`, `parentId?`, `timestamp`, `type`, `status?`). Frontend
reducer rules: dedup by event `id`, `timestamp` is authoritative order, `parentId`
links tool results to tool starts, malformed events are logged + skipped (never crash),
no free-text parsing to infer state.

**Transport constraints**: hosts adapt the `RpcApplication` protocol
(`dispatch_rpc_request`, `route_rpc_response`, `emit_response`). TCP host is
loopback-only by default, one active client, extra clients queued, serialized writes.
The WS host must mirror all of that.

### 2.2 Checkout reality (this machine, 2026-07-03)

The working tree tracks **docs/plans only** — `src/autocode/` contains only
`__pycache__`; `autocode/` workspace member is absent; `uv sync` fails. Therefore:

- Real-backend wiring **cannot be implemented or tested here**.
- Strategy: build against a **mock harness server** that emulates the documented
  protocol exactly, plus a **drop-in `ws_host.py`** written against the documented
  `RpcApplication` protocol for builders to integrate in the real source checkout.

## 3. Architecture

```
ui-designs/
  AutoCode.dc.html, support.js      # design source (do not modify)
  AutoCode.html                     # standalone prototype (keep working, do not break)
  harness-coverage.md
  webui/
    index.html                      # shell; loads modules; ?demo=1 forces demo mode
    styles.css                      # extracted CSS (reset, keyframes, hover/active utils)
    rpc.js                          # WebSocket JSON-RPC 2.0: id↔Promise correlation,
                                    #   notification dispatch, server-initiated request
                                    #   handling (reply路由), reconnect w/ backoff
    events.js                       # AgentEvent reducer → UI row/state model
                                    #   (dedup, timestamp sort, parentId linking)
    app.js                          # views + actions (ported from AutoCode.html);
                                    #   store-driven re-render w/ focus/scroll preservation
    demo.js                         # current hardcoded demo data + simulated actions
    mock-server.py                  # uv-runnable (PEP 723 inline deps: websockets);
                                    #   emulates all methods + notification streams,
                                    #   approval round-trip, scripted scenario
    backend/
      ws_host.py                    # drop-in adapter for autocode/src/autocode/backend/
      README.md                     #   integration notes for builders
    tests/
      reducer_test.js               # deno test: event taxonomy → UI state
      ui_smoke.js                   # deno DOM-stub smoke (port of session smoke, 47+ checks)
      test_mock_protocol.py         # pytest/uv: handshake, method responses, approval RTT
    test-results/                   # verification evidence per task (timestamped md)
```

Principles: **zero build step** (vanilla JS modules, no bundler — repo is Python/Rust);
demo mode stays fully functional offline (`?demo=1` or when WS connect fails, banner +
demo data); one WS connection; loopback only; UI never blocks on the backend
(optimistic composer, event-driven everything).

## 4. Surface → protocol wiring map

| UI surface (prototype) | Requests | Events consumed |
|---|---|---|
| Sidebar thread lists, search, Home cards | `session.list` | `on_status` (session meta) |
| New thread / open thread | `session.new`, `session.resume` | `on_chat_ack` |
| Composer send (home + thread) | `chat` | `on_token`, `on_thinking`, `on_done` |
| Stop/steer (add: Esc in thread) | `cancel`, `steer` | `on_done(cancelled)` |
| Plan card | `plan.status`, `plan.set` | `on_task_state` (until `PlanEvent` ships) |
| Act cards (read/term/edit) | — | `on_tool_call` (status: pending→running→done/failed) |
| Approval card | reply to server request | `on_tool_request` |
| Ask-user (new, maps to approval card variant) | reply to server request | `on_ask_user` |
| Thinking indicator | — | `on_thinking` |
| Model/mode/reasoning pickers, Settings | `model.list`, `provider.list`, `config.get/set` | `on_status` |
| Skills popover + Skills page | `command.list`, `command` | — |
| Usage meter / Plan & usage | — | `on_cost_update` |
| Review rail diff | `command` (`/diff`) — payload shape TBD | `DiffEvent` (planned upstream) |
| Automations page | display-only Phase 1 (`/watch`,`/loop` seeds) | — |
| Editor pane | Phase 2 (LSP surface not yet RPC-exposed) | — |
| Errors / recovery banner (new) | — | `on_error`, `on_warning` |

Policy adjustments vs. the design mock: "Commit staged & open PR" →
"Copy patch" + disabled PR button with tooltip (repo policy: agents never commit;
Director owns git). "Cloud" mode option disabled with "not available" note.

## 5. Task breakdown (Opus subagents)

Disjoint file ownership; parallel where independent. Every task: no git commands
beyond read-only status/diff (git-write-guard enforces), verification evidence file
under `ui-designs/webui/test-results/<YYYYMMDD-HHMMSS>-<task>.md`.

- **T1 — Protocol core + mock harness** (`rpc.js`, `events.js`, `mock-server.py`,
  `tests/reducer_test.js`, `tests/test_mock_protocol.py`).
  Exit gate: deno reducer tests green; `uv run mock-server.py` serves; pytest
  handshake/approval-round-trip green.
- **T2 — WebUI port** (`index.html`, `styles.css`, `app.js`, `demo.js`,
  `tests/ui_smoke.js`). Port AutoCode.html preserving visual fidelity + demo mode;
  introduce store/action seam where T3 will plug RPC.
  Exit gate: deno ui_smoke green (≥ the 47 prototype checks); `?demo=1` works from
  `file://`.
- **T3 — Wiring** (edits `app.js` + small `wiring.js`; depends on T1+T2).
  Connect map from §4: sessions, chat streaming, tool calls, approvals, thinking,
  cost, settings, skills. Live-vs-demo switch; recovery banner on `on_error`.
  Exit gate: scripted e2e — mock server + deno DOM-stub client run a full turn
  (chat → tokens → tool_call → tool_request → approve → done) asserting transcript
  state; evidence file.
- **T4 — Backend drop-in** (`backend/ws_host.py`, `backend/README.md`).
  WS host adapter targeting documented `RpcApplication`; loopback-only bind,
  single-active-client + queueing, serialized writer task, static file serving of
  `webui/`. Written to be copied into the real checkout; include unit-test file
  builders can run there. Exit gate: py_compile clean; README handoff complete;
  message drafted for `AGENTS_CONVERSATION.MD` (not sent — user decides).

Sequencing: T1 ∥ T2 ∥ T4 → review → T3 → review + full verification.

## 6. Out of scope (this plan)

Real-backend integration testing (needs source checkout), cloud execution, editor
LSP wiring (completions/signature/inlay/ghost need new backend surface first),
commit/PR flows, multi-client WS, auth beyond loopback, Electron/Tauri packaging.

## 7. Risks / open questions

- Exact JSON-RPC envelopes (param/result shapes) are documented at method-name level
  only; mock server codifies our best reading and `backend/README.md` lists every
  assumption for builder verification against `rpc-schema-v1` fixtures.
- `on_tool_request`/`on_ask_user` reply-envelope assumption (server-initiated request)
  must be confirmed in the real dispatcher.
- Diff/review payload shape (`DiffEvent` still "planned" upstream) — Phase 1 renders
  from `on_tool_call` edit results; revisit when `DiffEvent` ships.
- CLAUDE.md repo-structure table describes `autocode/` which is absent here; plan
  assumes the documented paths for the drop-in target.

## 8. Acceptance criteria

- [ ] `ui-designs/webui/index.html?demo=1` reproduces the full prototype standalone.
- [ ] `uv run ui-designs/webui/mock-server.py` + live mode: full chat turn with
      streaming, tool cards, approval round-trip, cost update — no console errors.
- [ ] Reducer obeys agent-events.md contract (dedup, ordering, parentId, malformed-skip)
      with tests proving each rule.
- [ ] `ws_host.py` compiles, mirrors TCP host constraints, ships with integration README.
- [ ] All tests green: deno reducer + ui_smoke + pytest mock protocol; evidence files
      stored under `ui-designs/webui/test-results/`.
- [ ] Prototype `AutoCode.html` and design sources untouched.
