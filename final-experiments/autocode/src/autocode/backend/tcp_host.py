"""TCP JSON-RPC host adapter for backend applications."""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
from typing import TYPE_CHECKING, Any

from autocode.backend.transport import (
    BackendTransport,
    decode_message,
    encode_message,
    process_rpc_message,
)

if TYPE_CHECKING:
    from autocode.backend.server import BackendServer


def is_loopback_bind_host(host: str) -> bool:
    """Return true when a TCP bind host stays on the local machine."""
    normalized = host.strip().strip("[]").lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


class TcpStreamTransport(BackendTransport):
    """Transport backed by an asyncio stream writer."""

    def __init__(self, writer: asyncio.StreamWriter) -> None:
        self._writer = writer
        self._loop = asyncio.get_running_loop()
        self._queue: asyncio.Queue[str | None] = asyncio.Queue()
        self._writer_task = self._loop.create_task(self._write_loop())

    def send_message(self, msg: dict[str, Any]) -> None:
        self._queue.put_nowait(encode_message(msg))

    async def _write_loop(self) -> None:
        while True:
            payload = await self._queue.get()
            try:
                if payload is None:
                    return
                self._writer.write(payload.encode("utf-8"))
                with contextlib.suppress(ConnectionResetError, BrokenPipeError, RuntimeError):
                    await self._writer.drain()
            finally:
                self._queue.task_done()

    async def aclose(self) -> None:
        """Flush queued writes and stop the transport writer task."""
        await self._queue.join()
        self._queue.put_nowait(None)
        with contextlib.suppress(ConnectionResetError, BrokenPipeError, RuntimeError):
            await self._writer_task


class TcpJsonRpcHost:
    """Serve one backend application over localhost TCP JSON-RPC."""

    def __init__(
        self,
        app: BackendServer,
        *,
        bind_host: str = "127.0.0.1",
        port: int = 8765,
    ) -> None:
        if not is_loopback_bind_host(bind_host):
            raise ValueError(
                "Refusing non-loopback TCP bind host by default; use 127.0.0.1 or localhost."
            )
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
                await transport.aclose()
                self._app.set_transport(None)
                writer.close()
                await writer.wait_closed()
