# SESSION HANDOFF — AutoCode IDE GUI + WebUI harness integration

_Updated 2026-07-03 (Asia/Dhaka). Both phases COMPLETE and verified. Read
`PLAN.md` / `TODO.md` / `TESTING.md` here and `../docs/plan/webui-integration-plan.md`._

## TL;DR — DONE

- **Phase 1 (implement the Claude Design mockup):** `AutoCode.html` — self-contained IDE
  GUI, 47/47 smoke checks. Complete.
- **Phase 2 (make it work with our harness):** `webui/` — browser frontend that speaks the
  documented JSON-RPC/WebSocket protocol, a protocol-conformant mock harness, and a
  drop-in `ws_host.py` for the real backend. **All 92 automated checks green.** Complete.

The three subagents that started Phase 2 died on a shared session limit; the main session
finished and verified the remaining files (rpc.js, mock-server.py, wiring.js, index.html,
all tests, backend README) directly.

## Verification (all green — see `webui/test-results/20260703-155051-verification.md`)

| Gate | Command | Result |
|---|---|---|
| Reducer contract | `deno test --allow-read webui/tests/reducer_test.js` | 8 passed |
| Mock protocol | `pytest webui/tests/test_mock_protocol.py` | 6 passed |
| UI smoke (demo) | `deno run --allow-read webui/tests/ui_smoke.js` | 57 checks |
| **Live e2e** | `deno run --allow-read --allow-net --allow-run --allow-env webui/tests/e2e_live.js` | 10 checks |
| ws_host adapter | `pytest webui/backend/test_ws_host.py` | 11 passed |

The live e2e is the real proof: it spawns the mock harness (real WebSocket) and drives the
actual client stack (rpc.js + events.js + demo.js + app.js + wiring.js) through a full turn
— connect → session list → streamed tokens → tool cards → server-initiated approval →
approve → done → cost + config round-trips.

## Run it yourself

```bash
# demo mode (offline, no backend):
open ui-designs/webui/index.html?demo=1          # or just index.html

# live mode against the mock harness:
uv run --no-project webui/mock-server.py         # terminal 1
open ui-designs/webui/index.html?live=1          # terminal 2  (badge shows ● live)
```

## File map (`ui-designs/`)

- `AutoCode.dc.html`, `support.js` — Claude Design source (do not modify; needs the Design runtime).
- `AutoCode.html` — Phase-1 standalone prototype (untouched by Phase 2).
- `harness-coverage.md` — UI surface ↔ `../docs/features/inventory.md` map.
- `webui/` — Phase-2 frontend:
  - `rpc.js` (WS JSON-RPC client), `events.js` (AgentEvent reducer), `wiring.js`
    (`window.Live` bridge), `app.js` + `demo.js` + `styles.css` + `index.html` (ported UI),
    `mock-server.py` (dev harness), `backend/ws_host.py` + `README.md` (real-backend drop-in),
    `tests/` (reducer, mock protocol, ui smoke, live e2e), `test-results/` (evidence).

## What's real vs. deferred

- **Real backend not in this checkout** (`src/autocode/` = only `__pycache__`). Everything is
  verified mock-first; `webui/backend/ws_host.py` is the drop-in for the real repo, and its
  README lists every assumption (chiefly whether `dispatch_rpc_request` returns vs. emits the
  response, and the approval request path) to VERIFY against `rpc-schema-v1` fixtures.
- **Policy honored:** no real git from the UI (agents never commit — Director commits). The
  "Commit & open PR" button remains demo-only; the plan calls for it to become "Copy patch".
- **Deferred (plan §6):** editor LSP wiring (completions/signature/inlay/ghost need new backend
  surface), cloud mode, multi-client, auth beyond loopback.

## Next step for a builder (real-backend integration)

Adopt `webui/backend/ws_host.py` into `autocode/src/autocode/backend/`, add `websockets>=12`,
wire a `--transport ws` branch on `autocode serve`, and reconcile the mock's envelopes with the
real dispatcher per the five VERIFY items in `webui/backend/README.md`. A ready-to-paste
`AGENTS_CONVERSATION.MD` message is drafted at the bottom of that README (paste it yourself).

## Environment gotchas

- `deno` for JS (no `node`); `bun` also present.
- `uv` workspace is broken here — always `uv run --no-project --with <deps> …`.
- Windows: killing `uv` does not kill its `python` child; the e2e tree-kills via `taskkill /F /T`
  and the mock has a `--max-seconds` watchdog. No orphans remain after test runs (verified).
- git-write-guard blocks mutating git; the user commits.

## Loose end

A project-memory write was **rejected** by the user earlier this session (nothing saved). Ask
before re-proposing a `ui-designs-ide-gui` memory.
