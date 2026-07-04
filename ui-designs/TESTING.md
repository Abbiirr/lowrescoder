# Testing — AutoCode WebUI Integration

Run all commands from `K:/projects/ai/lowrescoder/ui-designs`. Environment: `deno` for JS
(no node); `uv` for Python but **always** pass `--no-project` (workspace is broken).
Every task also drops an evidence file in `webui/test-results/<YYYYMMDD-HHMMSS>-<task>.md`.

## Task 1 — Protocol core + mock harness

Criteria:
- `rpc.js` exposes `window.RPC` (connect/reconnect, request↔Promise by id, notify,
  onNotification, onServerRequest for approvals, close).
- `events.js` reducer obeys the `agent-events.md` contract: dedup by id, timestamp
  ordering, parentId links tool-result→start, malformed events skipped (never throw).
- `mock-server.py` serves a full scripted turn incl. server-initiated approval round-trip.

Closing gate:
```bash
deno test --allow-read webui/tests/reducer_test.js
uv run --no-project --with websockets,pytest,pytest-asyncio python -m pytest webui/tests/test_mock_protocol.py -q
```

## Task 2 — WebUI port

Criteria:
- `index.html?demo=1` reproduces the prototype standalone from `file://`.
- Visuals/behavior identical to `AutoCode.html`; all `/* LIVE SEAM */` hooks present.

Closing gate:
```bash
deno run --allow-read webui/tests/ui_smoke.js   # >= the 47 prototype checks pass
```

## Task 3 — Live wiring

Criteria:
- `wiring.js` (`window.Live`) connects seams to RPC+Reducer per plan §4; demo mode still
  works when the socket is absent; `on_error` raises a recovery banner.

Closing gate:
```bash
# scripted end-to-end: mock server + DOM-stub client drive one full turn
# (chat -> on_token -> on_tool_call -> on_tool_request -> approve -> on_done)
deno run --allow-read --allow-net webui/tests/e2e_live.js
```

## Task 4 — Backend WS drop-in

Criteria:
- `ws_host.py` mirrors the TCP host: loopback-only bind, single active client + FIFO
  queue, serialized writer task, malformed JSON -> -32700, static file serving w/o
  traversal. `README.md` lists every backend assumption to verify + a builder handoff draft.

Closing gate:
```bash
uv run --no-project --with websockets,pytest,pytest-asyncio python -m pytest webui/backend/test_ws_host.py -q
```

## Task 5 — Full verification + handoff

Criteria:
- All gates above green; `AutoCode.html` + `AutoCode.dc.html` + `support.js` untouched
  (`git diff --stat` shows only additions under `webui/`); evidence files present.

Closing gate:
```bash
deno test --allow-read webui/tests/reducer_test.js
deno run --allow-read webui/tests/ui_smoke.js
uv run --no-project --with websockets,pytest,pytest-asyncio python -m pytest webui/tests/test_mock_protocol.py webui/backend/test_ws_host.py -q
git status --short   # only webui/ additions; prototype + design sources unchanged
```
