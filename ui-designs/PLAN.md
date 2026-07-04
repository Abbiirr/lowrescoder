# Plan — AutoCode WebUI Integration

## Goal

Turn the static IDE GUI prototype (`AutoCode.html`, an implementation of the Claude
Design mockup `AutoCode.dc.html`) into a working browser frontend for the AutoCode
harness backend: a WebSocket JSON-RPC client speaking the backend's documented
protocol, a protocol-conformant mock server for offline dev/verification, and a
drop-in WebSocket host adapter for the real backend. **All features working**, verified
by automated tests. The GUI is a *second* frontend beside the canonical Rust TUI —
same backend, same event contract, different surface.

Full architect spec: **`../docs/plan/webui-integration-plan.md`** (this file is the
builder-facing execution view; that file is the design of record).

## Context And References

- Prototype (works standalone, do not break): `AutoCode.html` — 47/47 DOM-stub smoke checks pass.
- Design source (do not modify): `AutoCode.dc.html`, `support.js` (needs Claude Design React runtime).
- Surface→harness map: `harness-coverage.md`.
- Protocol ground truth: `../docs/features/agent-events.md` (event taxonomy + reducer contract),
  `../docs/features/backend_features.md` (frontend-facing RPC method list),
  `../docs/features/inventory.md` (harness feature inventory).
- **Backend sources are NOT in this checkout** (`src/autocode/` has only `__pycache__`,
  `autocode/` workspace member absent, `uv sync` fails). Work is mock-first; the real
  backend adapter (`webui/backend/ws_host.py`) is a drop-in builders copy into the real repo.

## Approach

Build under `webui/` (zero build step — vanilla JS classic scripts, no bundler):

- `rpc.js` — WebSocket JSON-RPC 2.0 client (id↔Promise correlation, notifications,
  server-initiated request handling for approvals, reconnect/backoff).
- `events.js` — pure `AgentEvent` reducer implementing the documented contract (dedup by
  id, timestamp ordering, parentId linking, malformed-skip) → UI row/state model.
- `app.js` + `demo.js` + `index.html` + `styles.css` — the prototype ported to modules,
  with `?demo=1` offline mode and marked `LIVE SEAM` hooks.
- `wiring.js` (`window.Live`) — connects the seams to `RPC`+`Reducer` (T3).
- `mock-server.py` — `uv run --no-project` server emulating every method + a scripted turn
  incl. approval round-trip.
- `backend/ws_host.py` — drop-in host mirroring the TCP host's constraints (loopback-only,
  single active client + queue, serialized writes) + static file serving of `webui/`.

Compatibility / non-goals: prototype and design sources stay untouched; demo mode must
keep working offline; loopback only; **no real git from the UI** (repo policy — agents
never commit; the "Commit & open PR" button becomes "Copy patch" + disabled PR). Editor
LSP wiring, cloud mode, and multi-client are out of scope (see plan §6).

## Risks And Decisions

- Exact JSON-RPC param/result envelopes are documented at method-name level only; the
  mock codifies our reading and `backend/README.md` lists every assumption to verify
  against `rpc-schema-v1` fixtures in the real checkout.
- `on_tool_request`/`on_ask_user` assumed to be server-initiated JSON-RPC *requests* the
  client answers — must be confirmed against the real dispatcher.
- Diff/review payload (`DiffEvent`) is still "planned" upstream; Phase 1 renders diffs
  from `on_tool_call` edit results.
- Decision: builder implements T3 + completes any subagent-started task; architect
  (Claude) reviews. No commits by any agent — the Director (user) commits.
