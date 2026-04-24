"""Transport-host smoke tests for stdio and TCP backend shapes."""

from __future__ import annotations

import asyncio
import io
import json
import socket
from typing import Any

import pytest

from autocode.backend.stdio_host import StdioJsonRpcHost
from autocode.backend.tcp_host import TcpJsonRpcHost


class FakeRpcApp:
    def __init__(self) -> None:
        self._running = True
        self._transport = None
        self.dispatched: list[tuple[str, dict[str, Any], int]] = []
        self.responses: list[tuple[int, dict[str, Any]]] = []

    def set_transport(self, transport) -> None:
        self._transport = transport

    def _emit_status(self) -> None:
        assert self._transport is not None
        self._transport.send_message(
            {"jsonrpc": "2.0", "method": "on_status", "params": {"ready": True}}
        )

    async def _dispatch(self, method: str, params: dict[str, Any], request_id: int) -> None:
        self.dispatched.append((method, params, request_id))
        self.emit_response(request_id, {"ok": True, "method": method})
        self._running = False

    def _route_response(self, request_id: int, result: dict[str, Any]) -> None:
        self.responses.append((request_id, result))

    def emit_response(self, request_id: int, result: Any) -> None:
        assert self._transport is not None
        self._transport.send_message({"jsonrpc": "2.0", "id": request_id, "result": result})


@pytest.mark.asyncio
async def test_stdio_host_drives_same_application_surface() -> None:
    app = FakeRpcApp()
    stdin = io.StringIO('{"jsonrpc":"2.0","id":1,"method":"ping","params":{"value":1}}\n')
    stdout = io.StringIO()

    await StdioJsonRpcHost(app, stdin=stdin, stdout=stdout).run()

    lines = [json.loads(line) for line in stdout.getvalue().splitlines() if line.strip()]
    assert lines[0]["method"] == "on_status"
    assert lines[1]["id"] == 1
    assert lines[1]["result"] == {"ok": True, "method": "ping"}
    assert app.dispatched == [("ping", {"value": 1}, 1)]


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.mark.asyncio
async def test_tcp_host_drives_same_application_surface() -> None:
    app = FakeRpcApp()
    port = _free_tcp_port()
    host = TcpJsonRpcHost(app, bind_host="127.0.0.1", port=port)

    host_task = asyncio.create_task(host.run())
    reader = writer = None
    try:
        for _ in range(50):
            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", port)
                break
            except OSError:
                await asyncio.sleep(0.02)
        assert reader is not None
        assert writer is not None

        status_line = await reader.readline()
        writer.write(b'{"jsonrpc":"2.0","id":2,"method":"ping","params":{"value":2}}\n')
        await writer.drain()
        response_line = await reader.readline()

        status = json.loads(status_line.decode("utf-8"))
        response = json.loads(response_line.decode("utf-8"))

        assert status["method"] == "on_status"
        assert response["id"] == 2
        assert response["result"] == {"ok": True, "method": "ping"}
        assert app.dispatched == [("ping", {"value": 2}, 2)]
    finally:
        if writer is not None:
            writer.close()
            await writer.wait_closed()
        app._running = False
        await asyncio.wait_for(host_task, timeout=2)
