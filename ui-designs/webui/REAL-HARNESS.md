# Running the WebUI against the REAL AutoCode harness

The WebUI is protocol-complete and verified against a mock harness, but **the real
AutoCode backend source is not in this checkout** (this is the docs/planning repo;
`src/autocode/` is gitignored and holds only stale bytecode — no `.py`, nothing named
`autocode` is runnable). So the real backend can't run *here*. This guide is how to
connect the WebUI to the real harness **wherever it actually lives**, and how to point
the Start Menu app at it.

Nothing below has been executed against the real backend from this checkout — the parts
that must be confirmed against it are marked **VERIFY**. The bridge's own plumbing *is*
tested (`tests/test_ws_bridge.py`, 3/3).

## The one gap: transport

The backend speaks JSON-RPC over **stdio** and **TCP** (`autocode serve --transport
tcp`). Browsers can't open raw TCP sockets, so the WebUI needs a **WebSocket** entry
point. Two ways to provide it:

- **Option A — WS↔TCP bridge (recommended, zero backend changes).** Run `ws-bridge.py`
  in front of `autocode serve --transport tcp`. This is what the real launcher uses.
- **Option B — native `--transport ws`.** Adopt `backend/ws_host.py` into the backend and
  add a `ws` transport. More work, but one process. See `backend/README.md`.

Both reuse the same UI, reducer, and event contract — only the transport differs.

## Prerequisites

A working AutoCode checkout **elsewhere** where this runs cleanly:

```bash
cd <your autocode repo>
uv sync
uv run autocode serve --transport tcp --host 127.0.0.1 --port 8930
```

(In this checkout `uv sync` fails and there is no `autocode` package — that's expected.)

## Option A — run it now with the bridge

```bash
# 1) real backend (from the real autocode repo):
uv run autocode serve --transport tcp --host 127.0.0.1 --port 8930

# 2) bridge + UI (from THIS repo, ui-designs/):
uv run --no-project webui/ws-bridge.py --backend-port 8930 --framing newline
#    -> prints:  UI_URL http://127.0.0.1:<port>/index.html?live=1

# 3) open that URL (or use the Start Menu app, below)
```

The page loads over HTTP from the bridge and connects its WebSocket back to the same
origin; the bridge forwards every frame to/from the backend's TCP port. The UI's
`?demo=1` still gives the offline mock; `?live=1` (default when served) uses the bridge.

## Make the Start Menu app run the real harness

1. Edit **`harness.config.ps1`** — set `BackendCwd` to your real autocode repo, and
   adjust `BackendPort` / `BackendArgs` / `Framing` if needed.
2. Install (defaults to the real launcher):
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File webui\install-start-menu.ps1
   ```
3. Start menu → **AutoCode**. The launcher (`launch-autocode-real.ps1`) starts the
   backend, waits for its TCP port, starts the bridge, and opens the app window. On
   close it tears both down. If the backend isn't configured or won't start, it shows a
   dialog telling you what to fix (it will **not** silently fall back to the demo).

Dev/offline demo instead: `install-start-menu.ps1 -Mock` (targets the mock launcher).

## VERIFY against the real backend (do this before trusting it)

1. **TCP framing** — how `tcp_host.py` delimits messages on the wire. The bridge defaults
   to newline-delimited JSON (`--framing newline`); if the host uses LSP-style
   `Content-Length:` headers, use `--framing lsp` (and set `Framing = 'lsp'` in the
   config). Check `autocode/src/autocode/backend/tcp_host.py` and the
   `autocode/tests/pty/fixtures/rpc-schema-v1/` fixtures.
2. **Method + result envelopes** — the WebUI issues `session.list`, `session.new`,
   `session.resume`, `chat`, `cancel`, `config.get/set`, `command.list`, etc. Confirm the
   real param/result shapes match what `wiring.js` reads and what `mock-server.py`
   models. `mock-server.py` is the reference for the client-facing shapes; reconcile any
   differences there (and in `wiring.js` if a field is named differently).
3. **Notifications** — the reducer (`events.js`) consumes `on_token`, `on_thinking`,
   `on_tool_call`, `on_done`, `on_status`, `on_error`, `on_warning`, `on_cost_update`,
   `on_task_state`, `on_chat_ack`, `on_tool_request`, `on_ask_user`. These are the
   backend's own contract (`docs/features/agent-events.md`), so a conformant backend
   already matches. Any that carry different field names → adjust the matching handler in
   `events.js` (each handler is small and reads a couple of fields).
4. **Approvals** — `on_tool_request` / `on_ask_user` must be **server-initiated JSON-RPC
   requests** whose client response carries the decision. `wiring.js` replies via
   `RPC.onServerRequest`; the bridge forwards it as a normal frame. Confirm the real host
   emits these as requests (with an `id`), not fire-and-forget notifications.
5. **Streaming token ids** — each `on_token` should be a distinct event id; the reducer
   groups tokens into the in-progress answer row (it dedups by id, so reused ids drop
   tokens — a real bug the mock hit and we fixed).

## Where the pieces are

| File | Role |
|---|---|
| `ws-bridge.py` | WS↔TCP bridge to `autocode serve --transport tcp` (Option A) |
| `backend/ws_host.py` + `backend/README.md` | native `--transport ws` host (Option B) |
| `harness.config.ps1` | points the launcher at your real backend |
| `launch-autocode-real.ps1` | Start Menu launcher (real backend + bridge + app) |
| `launch-autocode.ps1` | dev/demo launcher (mock backend) — `-Mock` install only |
| `mock-server.py` | reference impl of the client-facing protocol; dev/offline backend |
| `wiring.js` / `events.js` / `rpc.js` | the client: seams, reducer, JSON-RPC client |
| `docs/features/agent-events.md`, `backend_features.md` | the protocol contract |

## When the backend changes something

Because the bridge is a transparent reframer, most contract adjustments are made in two
client files only: **`wiring.js`** (request params / result reading) and **`events.js`**
(notification field mapping). Keep `mock-server.py` in sync so the offline demo and the
tests keep exercising the same shapes.
