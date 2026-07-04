# /// script
# requires-python = ">=3.11"
# dependencies = ["websockets>=12", "pytest>=8", "pytest-asyncio>=0.23"]
# ///
"""
Mechanics test for webui/ws-bridge.py.

Stands up a FAKE TCP JSON-RPC backend (newline- and LSP-framed) and drives the
bridge through a real WebSocket client, asserting bidirectional forwarding. This
proves the bridge plumbing/reframing is correct WITHOUT the real AutoCode backend
(which is absent from this checkout). The real-backend contract itself is verified
separately per REAL-HARNESS.md.

Run:
  uv run --no-project --with websockets --with pytest --with pytest-asyncio \
      python -m pytest webui/tests/test_ws_bridge.py -q
"""
from __future__ import annotations

import asyncio
import contextlib
import importlib.util
import json
import pathlib

import pytest
import websockets

HERE = pathlib.Path(__file__).resolve()
BRIDGE_PATH = HERE.parent.parent / "ws-bridge.py"
pytestmark = pytest.mark.asyncio


def load_bridge():
    spec = importlib.util.spec_from_file_location("ws_bridge", BRIDGE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeBackend:
    """A trivial TCP JSON-RPC server: echoes requests as results and emits a
    notification after the first request. Speaks the chosen framing."""

    def __init__(self, framing: str):
        self.framing = framing
        self.server = None
        self.port = 0

    async def start(self):
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]

    async def _read(self, reader):
        if self.framing == "lsp":
            headers = {}
            while True:
                line = await reader.readline()
                if not line:
                    return None
                line = line.strip()
                if not line:
                    break
                k, _, v = line.partition(b":")
                headers[k.strip().lower()] = v.strip()
            n = int(headers.get(b"content-length", b"0"))
            return await reader.readexactly(n) if n else b""
        line = await reader.readline()
        return line.rstrip(b"\r\n") if line else None

    def _frame(self, payload: bytes) -> bytes:
        if self.framing == "lsp":
            return b"Content-Length: %d\r\n\r\n%s" % (len(payload), payload)
        return payload + b"\n"

    async def _handle(self, reader, writer):
        first = True
        while True:
            raw = await self._read(reader)
            if raw is None:
                break
            msg = json.loads(raw)
            # respond to the request
            resp = {"jsonrpc": "2.0", "id": msg.get("id"), "result": {"echo": msg.get("method")}}
            writer.write(self._frame(json.dumps(resp).encode()))
            await writer.drain()
            if first:
                first = False
                note = {"jsonrpc": "2.0", "method": "on_token", "params": {"text": "hello from backend"}}
                writer.write(self._frame(json.dumps(note).encode()))
                await writer.drain()

    async def stop(self):
        self.server.close()
        with contextlib.suppress(Exception):
            await self.server.wait_closed()


@contextlib.asynccontextmanager
async def bridge_running(framing: str):
    mod = load_bridge()
    mod._STATIC_DIR = None  # no static serving in the test
    mod._ACTIVE = False
    backend = FakeBackend(framing)
    await backend.start()
    handler = mod.make_handler("127.0.0.1", backend.port, framing, single=False)
    server = await websockets.serve(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        yield port
    finally:
        server.close()
        with contextlib.suppress(Exception):
            await server.wait_closed()
        await backend.stop()


async def _roundtrip(framing: str):
    async with bridge_running(framing) as port:
        async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
            # request -> forwarded to backend -> result comes back
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "session.list", "params": {}}))
            seen = []
            for _ in range(2):
                raw = await asyncio.wait_for(ws.recv(), timeout=5)
                seen.append(json.loads(raw))
            by_kind = {("resp" if "id" in m else "note"): m for m in seen}
            assert by_kind["resp"]["result"]["echo"] == "session.list"
            assert by_kind["note"]["method"] == "on_token"
            assert by_kind["note"]["params"]["text"] == "hello from backend"


async def test_bridge_newline_framing():
    await _roundtrip("newline")


async def test_bridge_lsp_framing():
    await _roundtrip("lsp")


async def test_bridge_backend_unreachable_closes_ws():
    mod = load_bridge()
    mod._STATIC_DIR = None
    mod._ACTIVE = False
    handler = mod.make_handler("127.0.0.1", 1, "newline", single=False)  # port 1: refused
    server = await websockets.serve(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        with pytest.raises(websockets.ConnectionClosed):
            async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
                await ws.send(json.dumps({"id": 1, "method": "x"}))
                await asyncio.wait_for(ws.recv(), timeout=5)
    finally:
        server.close()
        with contextlib.suppress(Exception):
            await server.wait_closed()
