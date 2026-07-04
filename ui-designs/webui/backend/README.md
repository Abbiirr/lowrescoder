# ws_host.py — WebSocket host for the AutoCode WebUI (builder handoff)

`ws_host.py` is a drop-in JSON-RPC host adapter that lets the browser WebUI
(`ui-designs/webui/`) talk to the AutoCode backend. Browsers can't speak the raw
TCP host, so this WebSocket host mirrors the TCP host's posture (loopback-only,
single active client, serialized writes) and can also serve the static WebUI files
on the same port.

It was written **against the documented `RpcApplication` contract only** — the real
backend sources are not in this checkout. Everything below marked **VERIFY** must be
checked against the real dispatcher before wiring it in.

## Where it goes

Copy into the backend package next to the existing hosts:

```
autocode/src/autocode/backend/ws_host.py     <- this file
```

Alongside `stdio_host.py` and `tcp_host.py` (per `docs/features/backend_features.md`
§ transport). Dependency to add to `autocode`'s deps: `websockets>=12`.

## What it provides

- `class WsHost(app, *, static_dir=None, queue_maxsize=64)`
- `await host.start(host="127.0.0.1", port=0, *, allow_remote=False) -> Server` — non-blocking; `port=0` binds ephemeral.
- `await host.serve(host, port, *, allow_remote=False)` — blocking run.
- `await host.shutdown()` — closes active + queued clients (code 1001).
- `await host.emit_response(client_id, message)` — the **outbound seam**: the app calls
  this (or the transport handle passed to `attach_transport`) to push responses,
  notifications, and server-initiated requests to the active client. All sends funnel
  through one back-pressure-aware writer task per connection.
- CLI demo: `python -m autocode.backend.ws_host --port 8765` (uses a built-in echo app).

Behaviors already covered by `test_ws_host.py` (11 tests, all passing here):
request dispatch round-trip, response routing for server-initiated requests, second
client queued then promoted on disconnect, ordered serialized writes, non-loopback
bind rejected, malformed JSON → `-32700`, static file serving + `../` traversal blocked.

## The RpcApplication contract this file assumes — **VERIFY each against the real backend**

```python
class RpcApplication(Protocol):
    async def dispatch_rpc_request(self, client_id: str, message: dict) -> dict | None: ...
    def route_rpc_response(self, client_id: str, message: dict) -> None: ...
    # optional: attach_transport(self, host) -> None   (outbound seam handshake)
```

1. **VERIFY** the real host protocol method names/signatures. `backend_features.md` names
   `dispatch_rpc_request`, `route_rpc_response`, `emit_response` on the `RpcApplication`
   protocol — confirm arities and whether `dispatch_rpc_request` returns the response dict
   (this file's assumption) or emits it out-of-band via `emit_response`. If the real app
   emits out-of-band, have `WsHost` pass itself as the transport (it already calls
   `attach_transport(self)` when present) and treat the return value as `None`.
2. **VERIFY** `client_id` shape/lifecycle expectations. This host mints `"ws-<n>"` ids;
   the TCP host may use a different scheme the app relies on.
3. **VERIFY** the server-initiated request path used by approvals: this host classifies an
   inbound frame with `id` and no `method` as a response and hands it to
   `route_rpc_response`; a frame with `method` (± `id`) goes to `dispatch_rpc_request`.
   Confirm `on_tool_request` / `on_ask_user` really are server→client *requests* whose
   client responses must reach `route_rpc_response` (this matches `agent-events.md`, but
   confirm against `autocode/tests/pty/fixtures/rpc-schema-v1/`).
4. **VERIFY** single-active-client semantics match the TCP host: this host queues extra
   clients (FIFO) and sends them `{"method":"on_status","params":{"queued":true,...}}`.
   The TCP host "queues additional clients behind the active connection" — confirm the
   queued-notification shape the frontend expects, if any.
5. **VERIFY** exact JSON-RPC envelopes (param/result field names) against the real
   dispatcher; the mock server (`../mock-server.py`) encodes this repo's best reading.

## Wiring a `--transport ws` flag on `autocode serve`

By analogy with the TCP host (`backend_features.md`: "JSON-RPC application split by
transport (stdio, tcp)"), add `ws` as a transport option:

```python
# in the serve command, after building the RpcApplication `app`:
elif transport == "ws":
    from autocode.backend.ws_host import WsHost
    host = WsHost(app, static_dir=webui_dir)          # webui_dir = repo/ui-designs/webui
    await host.serve(bind_host, port, allow_remote=allow_remote)
```

Keep the same loopback-default + `--host`/`--port` validation the TCP host uses
(`ws_host._validate_bind` already rejects non-loopback unless `allow_remote=True`).

## Serving the WebUI

`WsHost(app, static_dir=<ui-designs/webui>)` serves `index.html` + `*.css`/`*.js` over
plain HTTP GET on the same port (via the `websockets` `process_request` hook), with
content-types set and directory traversal blocked. Then the WebUI connects back to the
same origin:

```
open  http://127.0.0.1:8765/index.html?live=1
# or point the page at a specific socket:
open  http://127.0.0.1:8765/index.html?ws=ws://127.0.0.1:8765
```

## Run the tests here (before integrating)

```bash
uv run --no-project --with websockets --with pytest --with pytest-asyncio \
    python -m pytest ui-designs/webui/backend/test_ws_host.py -q
```

(One test is a sync function flagged with an `asyncio` mark — harmless warning; convert
it to a plain test or drop the mark when adopting.)

---

## Draft message for AGENTS_CONVERSATION.MD (paste it yourself — do not let an agent write to that log)

> **To: Builders — From: Claude (architect) — Re: WebUI ws_host adoption**
>
> The browser WebUI (`ui-designs/webui/`) is protocol-verified against a mock harness
> (10/10 live e2e, 8/8 reducer, 6/6 mock protocol, 11/11 ws_host, 57/57 UI smoke).
> To run it against the real backend, adopt `ui-designs/webui/backend/ws_host.py` into
> `autocode/src/autocode/backend/`, add `websockets>=12`, and wire a `--transport ws`
> branch on `autocode serve` (see that file's README). Before wiring, verify the five
> **VERIFY** items in the README against the real dispatcher and the `rpc-schema-v1`
> fixtures — chiefly whether `dispatch_rpc_request` returns the response or emits it via
> `emit_response`, and the server-initiated request path for approvals. Ping me with the
> confirmed signatures and I'll reconcile the mock + client envelopes.
