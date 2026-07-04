"""Unit tests for ws_host.WsHost against a fake RpcApplication.

Run (workspace is broken here, so always ``--no-project``)::

    uv run --no-project --with websockets,pytest,pytest-asyncio \
        python -m pytest ui-designs/webui/backend/test_ws_host.py -q

These tests exercise the host contract without the real backend:
request dispatch round-trip, server-initiated request/response routing,
single-active-client + FIFO queueing/promotion, serialized ordered writes,
non-loopback rejection, malformed-JSON -32700, and static file serving
(including directory-traversal blocking).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import urllib.error
import urllib.request

import pytest
import websockets

from ws_host import WsHost

pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------- #
# Fake application recording calls.
# --------------------------------------------------------------------------- #
class FakeApp:
    """Records dispatch/route calls and drives outbound emits via the host."""

    def __init__(self) -> None:
        self.host: WsHost | None = None
        self.dispatched: list[tuple[str, dict]] = []
        self.routed: list[tuple[str, dict]] = []
        self.route_events: dict[str, asyncio.Event] = {}

    # Optional convenience hook the host calls at construction.
    def attach_transport(self, host: WsHost) -> None:
        self.host = host

    async def dispatch_rpc_request(self, client_id: str, message: dict):
        self.dispatched.append((client_id, message))
        method = message.get("method")
        msg_id = message.get("id")
        assert self.host is not None

        if method == "emit_burst":
            count = int(message.get("params", {}).get("count", 5))
            for i in range(count):
                await self.host.emit_response(
                    client_id,
                    {"jsonrpc": "2.0", "method": "on_token", "params": {"seq": i}},
                )
            if msg_id is not None:
                return {"jsonrpc": "2.0", "id": msg_id, "result": {"emitted": count}}
            return None

        if method == "trigger_approval":
            # Server-initiated request; do NOT await the reply here (would
            # deadlock the read loop). The reply comes back via route_rpc_response.
            await self.host.emit_response(
                client_id,
                {
                    "jsonrpc": "2.0",
                    "id": "srv-1",
                    "method": "on_tool_request",
                    "params": {"tool": "run_command"},
                },
            )
            if msg_id is not None:
                return {"jsonrpc": "2.0", "id": msg_id, "result": {"triggered": True}}
            return None

        if msg_id is not None:
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"echo": method}}
        return None

    # Intentionally sync to exercise the host's _maybe_await path.
    def route_rpc_response(self, client_id: str, message: dict) -> None:
        self.routed.append((client_id, message))
        event = self.route_events.get(str(message.get("id")))
        if event is not None:
            event.set()


# --------------------------------------------------------------------------- #
# Helpers.
# --------------------------------------------------------------------------- #
@contextlib.asynccontextmanager
async def running_host(app: FakeApp, **kwargs):
    host = WsHost(app, **kwargs)
    server = await host.start("127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        yield host, port
    finally:
        await host.shutdown()


def uri(port: int) -> str:
    return f"ws://127.0.0.1:{port}"


def _http_get(url: str) -> tuple[int, str, str]:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            body = resp.read().decode("utf-8", "replace")
            return resp.status, resp.headers.get("Content-Type", ""), body
    except urllib.error.HTTPError as exc:  # 404 etc.
        return exc.code, exc.headers.get("Content-Type", ""), exc.read().decode("utf-8", "replace")


# --------------------------------------------------------------------------- #
# Tests.
# --------------------------------------------------------------------------- #
async def test_request_dispatch_roundtrip():
    app = FakeApp()
    async with running_host(app) as (_host, port):
        async with websockets.connect(uri(port)) as ws:
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}))
            resp = json.loads(await ws.recv())

    assert resp["id"] == 1
    assert resp["result"]["echo"] == "ping"
    assert app.dispatched, "app should have received the dispatch"
    cid, msg = app.dispatched[0]
    assert cid.startswith("ws-")
    assert msg["method"] == "ping"


async def test_notification_gets_no_response():
    app = FakeApp()
    async with running_host(app) as (_host, port):
        async with websockets.connect(uri(port)) as ws:
            # No "id" -> notification -> no response frame; then a request to prove
            # the socket is still alive and ordered.
            await ws.send(json.dumps({"jsonrpc": "2.0", "method": "note"}))
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": 7, "method": "ping"}))
            resp = json.loads(await ws.recv())

    assert resp["id"] == 7  # only the request produced a frame
    methods = [m["method"] for _c, m in app.dispatched]
    assert methods == ["note", "ping"]


async def test_response_routing_server_initiated_request():
    app = FakeApp()
    app.route_events["srv-1"] = asyncio.Event()
    async with running_host(app) as (_host, port):
        async with websockets.connect(uri(port)) as ws:
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "trigger_approval"}))

            server_req = None
            for _ in range(2):  # server request + response to id=1
                frame = json.loads(await ws.recv())
                if frame.get("method") == "on_tool_request":
                    server_req = frame
            assert server_req is not None
            assert server_req["id"] == "srv-1"

            # Client replies to the server-initiated request.
            await ws.send(
                json.dumps({"jsonrpc": "2.0", "id": "srv-1", "result": {"approved": True}})
            )
            await asyncio.wait_for(app.route_events["srv-1"].wait(), timeout=3)

    assert app.routed, "route_rpc_response should have been called"
    _cid, reply = app.routed[0]
    assert reply["id"] == "srv-1"
    assert reply["result"]["approved"] is True


async def test_second_client_queued_then_promoted():
    app = FakeApp()
    async with running_host(app) as (_host, port):
        ws1 = await websockets.connect(uri(port))
        ws2 = await websockets.connect(uri(port))
        try:
            # ws2 is queued behind ws1 and told its position.
            status = json.loads(await ws2.recv())
            assert status["method"] == "on_status"
            assert status["params"] == {"queued": True, "position": 1}

            # First client leaves -> ws2 gets promoted to active.
            await ws1.close()

            await ws2.send(json.dumps({"jsonrpc": "2.0", "id": 42, "method": "after_promote"}))
            resp = json.loads(await asyncio.wait_for(ws2.recv(), timeout=3))
            assert resp["id"] == 42
            assert resp["result"]["echo"] == "after_promote"
        finally:
            await ws1.close()
            await ws2.close()


async def test_serialized_writes_preserve_order():
    app = FakeApp()
    burst = 25
    async with running_host(app) as (_host, port):
        async with websockets.connect(uri(port)) as ws:
            await ws.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "emit_burst",
                        "params": {"count": burst},
                    }
                )
            )
            received = [json.loads(await ws.recv()) for _ in range(burst + 1)]

    tokens = [m for m in received if m.get("method") == "on_token"]
    seqs = [m["params"]["seq"] for m in tokens]
    assert seqs == list(range(burst)), "notifications must arrive in emit order"
    # The response to the request is the final frame (emitted after the burst).
    assert received[-1].get("id") == 1
    assert received[-1]["result"]["emitted"] == burst


async def test_malformed_json_returns_parse_error():
    app = FakeApp()
    async with running_host(app) as (_host, port):
        async with websockets.connect(uri(port)) as ws:
            await ws.send("this is not json {")
            resp = json.loads(await ws.recv())

    assert resp["error"]["code"] == -32700
    assert resp["id"] is None
    assert app.dispatched == []  # never reached the app


async def test_non_object_json_returns_invalid_request():
    app = FakeApp()
    async with running_host(app) as (_host, port):
        async with websockets.connect(uri(port)) as ws:
            await ws.send(json.dumps([1, 2, 3]))  # valid JSON, not an object
            resp = json.loads(await ws.recv())

    assert resp["error"]["code"] == -32600
    assert resp["id"] is None


async def test_non_loopback_bind_rejected():
    app = FakeApp()
    host = WsHost(app)
    with pytest.raises(ValueError):
        await host.start("0.0.0.0", 0)
    # Validation-only checks (no real network bind on all interfaces):
    with pytest.raises(ValueError):
        host._validate_bind("192.168.1.10", allow_remote=False)
    # allow_remote overrides without raising.
    host._validate_bind("0.0.0.0", allow_remote=True)
    # Loopback forms are always allowed.
    host._validate_bind("127.0.0.1", allow_remote=False)
    host._validate_bind("::1", allow_remote=False)
    host._validate_bind("localhost", allow_remote=False)


async def test_static_serving_returns_index(tmp_path):
    (tmp_path / "index.html").write_text("<h1>AutoCode WebUI</h1>", encoding="utf-8")
    (tmp_path / "app.js").write_text("console.log('hi');", encoding="utf-8")
    app = FakeApp()
    async with running_host(app, static_dir=tmp_path) as (_host, port):
        status, ctype, body = await asyncio.to_thread(_http_get, f"http://127.0.0.1:{port}/")
        assert status == 200
        assert "text/html" in ctype
        assert "AutoCode WebUI" in body

        status, ctype, body = await asyncio.to_thread(
            _http_get, f"http://127.0.0.1:{port}/app.js"
        )
        assert status == 200
        assert "javascript" in ctype
        assert "console.log" in body

        status, _ctype, _body = await asyncio.to_thread(
            _http_get, f"http://127.0.0.1:{port}/does-not-exist.html"
        )
        assert status == 404


async def test_static_serving_disabled_returns_404():
    app = FakeApp()
    async with running_host(app, static_dir=None) as (_host, port):
        status, _ctype, _body = await asyncio.to_thread(_http_get, f"http://127.0.0.1:{port}/")
    assert status == 404


async def test_static_path_resolution_blocks_traversal(tmp_path):
    static_dir = tmp_path / "webui"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("ok", encoding="utf-8")
    # A secret OUTSIDE the served directory that traversal must not reach.
    (tmp_path / "secret.txt").write_text("top secret", encoding="utf-8")

    host = WsHost(FakeApp(), static_dir=static_dir)

    assert host._resolve_static_path("/") == (static_dir / "index.html").resolve()
    assert host._resolve_static_path("/index.html") == (static_dir / "index.html").resolve()

    # Directory traversal (raw, encoded, and query-suffixed) must be blocked.
    assert host._resolve_static_path("/../secret.txt") is None
    assert host._resolve_static_path("/%2e%2e/secret.txt") is None
    assert host._resolve_static_path("/../../etc/passwd") is None
    # Missing file inside the dir -> None (404).
    assert host._resolve_static_path("/missing.css") is None
    # Query string is stripped before resolution.
    assert host._resolve_static_path("/index.html?v=1") == (static_dir / "index.html").resolve()
