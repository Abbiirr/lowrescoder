"""TCP JSON-RPC host adapter for backend applications."""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any

from autocode.backend.transport import (
    BackendTransport,
    decode_message,
    encode_message,
    process_rpc_message,
)

if TYPE_CHECKING:
    from autocode.backend.server import BackendServer


class TcpStreamTransport(BackendTransport):
    """Transport backed by an asyncio stream writer."""

    def __init__(self, writer: asyncio.StreamWriter) -> None:
        self._writer = writer
        self._loop = asyncio.get_running_loop()

    def send_message(self, msg: dict[str, Any]) -> None:
        self._writer.write(encode_message(msg).encode("utf-8"))
        self._loop.create_task(self._drain())

    async def _drain(self) -> None:
        with contextlib.suppress(ConnectionResetError, BrokenPipeError, RuntimeError):
            await self._writer.drain()


class TcpJsonRpcHost:
    """Serve one backend application over localhost TCP JSON-RPC."""

    def __init__(
        self,
        app: BackendServer,
        *,
        bind_host: str = "127.0.0.1",
        port: int = 8765,
    ) -> None:
        self._app = app
        self._bind_host = bind_host
        self._port = port
        self._client_lock = asyncio.Lock()

    async def run(self) -> None:
        server = await asyncio.start_server(self._handle_client, self._bind_host, self._port)
        async with server:
            while self._app._running:
                await asyncio.sleep(0.05)
            server.close()
            await server.wait_closed()

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        async with self._client_lock:
            transport = TcpStreamTransport(writer)
            self._app.set_transport(transport)
            self._app._emit_status()
            try:
                while self._app._running:
                    line = await reader.readline()
                    if not line:
                        break
                    decoded = decode_message(line.decode("utf-8").strip())
                    if decoded is None:
                        continue
                    await process_rpc_message(self._app, decoded)
            finally:
                self._app.set_transport(None)
                writer.close()
                await writer.wait_closed()
