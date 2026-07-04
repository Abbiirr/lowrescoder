# /// script
# requires-python = ">=3.11"
# dependencies = ["websockets>=12", "pytest>=8", "pytest-asyncio>=0.23"]
# ///
"""
Protocol tests for webui/mock-server.py.

Run:
  uv run --no-project --with websockets --with pytest --with pytest-asyncio \
      python -m pytest webui/tests/test_mock_protocol.py -q

The mock is loaded in-process (its filename has a hyphen, so via importlib) and
served on the test's own event loop — this avoids the uv `--with` overlay not
being visible to a fresh `sys.executable` subprocess on Windows. Asserts the
documented behaviors:
  * session.list round-trip + model/command fixtures + config.set -> on_status
  * chat -> ordered notification stream (ack, thinking, tokens, tool calls)
  * on_tool_request arrives as a SERVER-INITIATED request; answering it unblocks
    the turn through on_done + on_cost_update
  * cancel mid-turn yields on_done(cancelled=True)
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
MOCK_PATH = HERE.parent.parent / "mock-server.py"

pytestmark = pytest.mark.asyncio


def load_mock():
    spec = importlib.util.spec_from_file_location("mock_server", MOCK_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Conn:
    def __init__(self, ws):
        self.ws = ws
        self._id = 0
        self.responses: dict = {}
        self.notifications: list = []
        self.server_requests: "asyncio.Queue" = asyncio.Queue()
        self._resp_events: dict = {}
        self._reader = asyncio.create_task(self._read())

    async def _read(self):
        with contextlib.suppress(websockets.ConnectionClosed):
            async for raw in self.ws:
                msg = json.loads(raw)
                if "method" in msg and "id" in msg:
                    await self.server_requests.put(msg)
                elif "method" in msg:
                    self.notifications.append(msg)
                elif "id" in msg:
                    self.responses[msg["id"]] = msg
                    ev = self._resp_events.get(msg["id"])
                    if ev:
                        ev.set()

    async def request(self, method, params=None, timeout=5):
        self._id += 1
        rid = self._id
        ev = asyncio.Event()
        self._resp_events[rid] = ev
        await self.ws.send(json.dumps({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}}))
        await asyncio.wait_for(ev.wait(), timeout)
        return self.responses[rid]

    async def respond(self, rid, result):
        await self.ws.send(json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}))

    async def wait_notify(self, method, timeout=6):
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            for n in self.notifications:
                if n.get("method") == method:
                    return n
            await asyncio.sleep(0.02)
        raise AssertionError(f"notification {method} not seen; got {[n['method'] for n in self.notifications]}")

    async def close(self):
        self._reader.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await self._reader
        await self.ws.close()


@contextlib.asynccontextmanager
async def serve():
    mod = load_mock()
    mod._active_client = False
    port = 0  # ephemeral
    async with websockets.serve(mod.handler, "127.0.0.1", port) as server:
        bound = list(server.sockets)[0].getsockname()[1]
        ws = await websockets.connect(f"ws://127.0.0.1:{bound}")
        c = Conn(ws)
        try:
            yield c
        finally:
            await c.close()


async def test_session_list_roundtrip():
    async with serve() as c:
        resp = await c.request("session.list")
        sessions = resp["result"]["sessions"]
        assert len(sessions) == 5
        assert sessions[0]["title"].startswith("Fix booking")


async def test_config_and_models():
    async with serve() as c:
        assert len((await c.request("model.list"))["result"]["models"]) == 3
        assert (await c.request("command.list"))["result"]["commands"][0]["cmd"] == "/review"
        r = await c.request("config.set", {"model": "AC-1 Fast"})
        assert r["result"]["ok"] is True
        n = await c.wait_notify("on_status")
        assert n["params"]["model"] == "AC-1 Fast"


async def test_unknown_method_errors():
    async with serve() as c:
        r = await c.request("does.not.exist")
        assert r["error"]["code"] == -32601


async def test_chat_stream_and_approval():
    async with serve() as c:
        await c.request("chat", {"text": "fix the double charge"})
        await c.wait_notify("on_chat_ack")
        await c.wait_notify("on_token")
        await c.wait_notify("on_tool_call")
        req = await asyncio.wait_for(c.server_requests.get(), timeout=6)
        assert req["method"] == "on_tool_request"
        assert "booking overlap" in req["params"]["command"]
        await c.respond(req["id"], {"decision": "allow"})
        await c.wait_notify("on_cost_update")
        done = await c.wait_notify("on_done")
        assert done["params"]["cancelled"] is False


async def test_deny_still_completes():
    async with serve() as c:
        await c.request("chat", {"text": "fix it"})
        req = await asyncio.wait_for(c.server_requests.get(), timeout=6)
        await c.respond(req["id"], {"decision": "deny"})
        done = await c.wait_notify("on_done")
        assert done["params"]["cancelled"] is False


async def test_cancel_mid_turn():
    async with serve() as c:
        await c.request("chat", {"text": "long task"})
        await c.wait_notify("on_chat_ack")
        await c.request("cancel")
        done = await c.wait_notify("on_done", timeout=8)
        assert done["params"]["cancelled"] is True
