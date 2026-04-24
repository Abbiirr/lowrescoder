"""Transport helpers for backend-host JSON-RPC communication."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol, TextIO

from autocode.core.logging import log_event

logger = logging.getLogger(__name__)


class BackendTransport(Protocol):
    """Concrete transport for sending JSON-RPC messages to a frontend client."""

    def send_message(self, msg: dict[str, Any]) -> None: ...


class RpcApplication(Protocol):
    """Application surface required by host adapters."""

    async def _dispatch(self, method: str, params: dict[str, Any], request_id: int) -> None: ...

    def _route_response(self, request_id: int, result: dict[str, Any]) -> None: ...

    def emit_response(self, request_id: int, result: Any) -> None: ...


def encode_message(msg: dict[str, Any]) -> str:
    """Encode one newline-delimited JSON-RPC message."""
    return json.dumps(msg, separators=(",", ":")) + "\n"


def decode_message(line_str: str) -> dict[str, Any] | None:
    """Decode one JSON-RPC line, logging malformed input."""
    try:
        return json.loads(line_str)
    except json.JSONDecodeError as exc:
        context_start = max(0, exc.pos - 80)
        context_end = min(len(line_str), exc.pos + 80)
        log_event(
            logger,
            logging.WARNING,
            "rpc_error",
            error="invalid_json",
            decode_error=str(exc),
            error_pos=exc.pos,
            line_length=len(line_str),
            line_preview=line_str[:200],
            line_suffix=line_str[-200:],
            error_context=line_str[context_start:context_end],
        )
        return None


@dataclass(slots=True)
class PendingRequestBroker:
    """Tracks pending frontend responses for backend-originated requests."""

    next_request_id: int
    pending_futures: dict[int, asyncio.Future[dict[str, Any]]] = field(default_factory=dict)

    async def emit_request(
        self,
        transport: BackendTransport | None,
        method: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        if transport is None:
            raise RuntimeError("No backend transport attached")

        request_id = self.next_request_id
        self.next_request_id += 1

        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        self.pending_futures[request_id] = future

        transport.send_message(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }
        )
        try:
            return await future
        finally:
            self.pending_futures.pop(request_id, None)

    def route_response(self, request_id: int, result: dict[str, Any]) -> None:
        future = self.pending_futures.get(request_id)
        if future and not future.done():
            future.set_result(result)

    def cancel_all(self, reason: str) -> None:
        """Fail any outstanding frontend-request futures."""
        for future in self.pending_futures.values():
            if not future.done():
                future.set_exception(RuntimeError(reason))
        self.pending_futures.clear()


class StdoutTransport:
    """Transport that writes newline-delimited JSON-RPC to a text stream."""

    def __init__(self, writer: TextIO | None = None) -> None:
        self._writer = writer

    def send_message(self, msg: dict[str, Any]) -> None:
        import sys

        writer = self._writer or sys.stdout
        writer.write(encode_message(msg))
        writer.flush()


async def process_rpc_message(app: RpcApplication, msg: dict[str, Any]) -> None:
    """Route one decoded JSON-RPC message into the application surface."""
    msg_id = msg.get("id")
    method = msg.get("method")

    if msg_id is not None and method is None:
        app._route_response(msg_id, msg.get("result", {}))
        return

    if method is None:
        return

    request_id = msg_id if msg_id is not None else 0
    params = msg.get("params", {})

    try:
        await app._dispatch(method, params, request_id)
    except Exception as exc:  # noqa: BLE001 - host returns structured backend error
        logger.exception("Error dispatching %s: %s", method, exc)
        if request_id:
            app.emit_response(request_id, {"error": str(exc)})
