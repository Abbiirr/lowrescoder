"""Stdio JSON-RPC host adapter for backend applications."""

from __future__ import annotations

import asyncio
import threading
from typing import TYPE_CHECKING, TextIO

from autocode.backend.transport import StdoutTransport, decode_message, process_rpc_message

if TYPE_CHECKING:
    from autocode.backend.server import BackendServer


class StdioJsonRpcHost:
    """Own stdin/stdout framing and lifecycle outside BackendServer."""

    def __init__(
        self,
        app: BackendServer,
        *,
        stdin: TextIO,
        stdout: TextIO,
    ) -> None:
        self._app = app
        self._stdin = stdin
        self._stdout = stdout

    async def run(self) -> None:
        self._app.set_transport(StdoutTransport(self._stdout))
        self._app._emit_status()

        loop = asyncio.get_running_loop()
        line_queue: asyncio.Queue[str | None] = asyncio.Queue()

        def _queue_line(line: str | None) -> None:
            try:
                loop.call_soon_threadsafe(line_queue.put_nowait, line)
            except RuntimeError:
                pass

        def _stdin_reader() -> None:
            try:
                for raw_line in self._stdin:
                    _queue_line(raw_line)
            except (EOFError, OSError, ValueError):
                pass
            finally:
                _queue_line(None)

        reader_thread = threading.Thread(target=_stdin_reader, daemon=True)
        reader_thread.start()

        while self._app._running:
            try:
                line_str_raw = await line_queue.get()
            except Exception:
                break

            if line_str_raw is None:
                break

            line_str = line_str_raw.strip()
            if not line_str:
                continue

            msg = decode_message(line_str)
            if msg is None:
                continue

            await process_rpc_message(self._app, msg)
