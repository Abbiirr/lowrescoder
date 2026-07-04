"""WebSocket JSON-RPC host adapter for the AutoCode backend harness.

This is a *drop-in* transport host, written to be copied into the real backend
checkout at ``autocode/src/autocode/backend/ws_host.py``. It is a sibling of the
documented ``stdio_host.py`` and ``tcp_host.py`` adapters and targets the same
public ``RpcApplication`` protocol.

Security / concurrency posture (mirrors the TCP host, see
``docs/features/backend_features.md`` §Runtime And Hosting):

* Loopback-only bind by default (``127.0.0.1`` / ``::1`` / ``localhost``);
  non-loopback binds are rejected unless ``allow_remote=True`` is passed, in
  which case a loud warning is logged.
* Exactly one *active* WebSocket client at a time. Additional clients are held
  in a FIFO queue, told their queue position via an ``on_status`` notification,
  and promoted to active when the current active client disconnects.
* All outbound frames (responses, notifications, server-initiated requests) for
  the active client are serialized through a single writer task consuming a
  bounded ``asyncio.Queue`` -- this provides ordering and back-pressure.
* Malformed inbound JSON never crashes the host; it produces a JSON-RPC
  ``-32700`` parse-error response.
* Optional static file serving of the WebUI directory over plain HTTP GET on the
  same port (via the websockets ``process_request`` hook), with directory
  traversal blocked.

Dependency: ``websockets>=12`` (developed and verified against ``websockets``
16.x, which exposes the ``websockets.asyncio`` server API).

IMPORTANT -- signatures to verify against the real backend before shipping:
    The ``RpcApplication`` protocol below encodes this adapter's *best reading*
    of the documented contract. The exact method names, sync/async-ness, and
    payload shapes MUST be reconciled against the real ``BackendServer`` /
    ``dispatcher.py`` and the ``rpc-schema-v1`` fixtures. Every assumption is
    listed in ``README.md`` (section "Assumptions to verify"). The code is
    defensive where cheap (awaits results that may or may not be coroutines) so
    that small signature differences do not require a rewrite.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import inspect
import ipaddress
import itertools
import json
import logging
import mimetypes
import signal
from collections import deque
from dataclasses import dataclass, field
from http import HTTPStatus
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional, Protocol, runtime_checkable

import websockets
from websockets.asyncio.server import Server, ServerConnection
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Request, Response

logger = logging.getLogger("autocode.backend.ws_host")

# Hosts that are considered safe (loopback) for a default local-first bind.
_LOOPBACK_HOSTNAMES = {"localhost", "127.0.0.1", "::1", ""}

# Sentinel pushed onto a writer queue to ask the writer task to stop cleanly.
_WRITER_STOP = object()

# WebSocket close code for "going away" / server shutdown (RFC 6455).
_CLOSE_GOING_AWAY = 1001


# --------------------------------------------------------------------------- #
# RpcApplication protocol (the seam against the real backend).
# --------------------------------------------------------------------------- #
@runtime_checkable
class RpcApplication(Protocol):
    """Minimal surface this host requires of the backend application.

    The documented contract names three members --
    ``dispatch_rpc_request``, ``route_rpc_response``, ``emit_response`` -- shared
    by ``stdio_host.py`` / ``tcp_host.py``. This adapter treats the first two as
    *inbound* handlers it calls on the app, and treats the outbound push
    (``emit_response`` and the ``emit_*`` family such as ``emit_cost_update``,
    per backend_features.md §Runtime line ~16) as *host-provided* methods the app
    calls. See ``README.md`` for the full direction rationale and what must be
    verified.
    """

    async def dispatch_rpc_request(
        self, client_id: str, message: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Handle an inbound request/notification.

        Returns a JSON-RPC *response* dict for requests (those carrying an
        ``id``) or ``None`` for notifications. May be implemented sync or async;
        this host awaits the result if it is awaitable. NOTE: the real signature
        must be verified against the backend dispatcher.
        """
        ...

    def route_rpc_response(
        self, client_id: str, message: dict[str, Any]
    ) -> Any:
        """Handle an inbound *response* to a server-initiated request.

        Used by the approval / ask-user flow: the server sends an
        ``on_tool_request`` / ``on_ask_user`` JSON-RPC request; the client
        replies with a JSON-RPC response and this host routes it here so the app
        can resolve the pending future. May be sync or async.
        """
        ...


# Outbound emitter type: the app calls this to push a frame to a client.
EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]


@runtime_checkable
class TransportAwareApp(Protocol):
    """Optional convenience hook. If the app implements ``attach_transport`` it
    is called once at host construction with the host instance, giving the app a
    handle to ``host.emit_response`` for outbound frames. Real backends may wire
    the outbound seam differently (e.g. constructor injection); this is only a
    best-effort convenience and is documented in ``README.md``.
    """

    def attach_transport(self, host: "WsHost") -> None:
        ...


# --------------------------------------------------------------------------- #
# Connection bookkeeping.
# --------------------------------------------------------------------------- #
@dataclass
class _ActiveConn:
    """State for the single active connection, including its writer queue."""

    client_id: str
    ws: ServerConnection
    queue: asyncio.Queue


@dataclass
class _Waiter:
    """A queued connection awaiting promotion to active."""

    client_id: str
    ws: ServerConnection
    promote_event: asyncio.Event = field(default_factory=asyncio.Event)
    active: Optional[_ActiveConn] = None


async def _maybe_await(value: Any) -> Any:
    """Await ``value`` if it is awaitable, else return it as-is.

    Lets this host tolerate either sync or async ``route_rpc_response`` /
    ``dispatch_rpc_request`` implementations in the real backend.
    """

    if inspect.isawaitable(value):
        return await value
    return value


# --------------------------------------------------------------------------- #
# The host.
# --------------------------------------------------------------------------- #
class WsHost:
    """WebSocket transport host adapting an ``RpcApplication``.

    Parameters
    ----------
    app:
        The backend application implementing ``RpcApplication``.
    static_dir:
        Optional directory served over plain HTTP GET on the same port. ``None``
        disables static serving (every non-WebSocket request gets 404).
    queue_maxsize:
        Bounded size of the per-connection outbound queue (back-pressure). ``0``
        means unbounded (not recommended).
    """

    def __init__(
        self,
        app: RpcApplication,
        *,
        static_dir: Optional[Path | str] = None,
        queue_maxsize: int = 64,
    ) -> None:
        self._app = app
        self._static_dir: Optional[Path] = (
            Path(static_dir).resolve() if static_dir is not None else None
        )
        self._queue_maxsize = queue_maxsize

        self._active: Optional[_ActiveConn] = None
        self._waiters: "deque[_Waiter]" = deque()
        self._server: Optional[Server] = None
        self._client_ids = itertools.count(1)
        self._closing = False

        # Best-effort outbound-seam wiring: hand the app a transport handle.
        attach = getattr(app, "attach_transport", None)
        if callable(attach):
            attach(self)

    # ------------------------------------------------------------------ #
    # Lifecycle.
    # ------------------------------------------------------------------ #
    async def start(
        self,
        host: str = "127.0.0.1",
        port: int = 0,
        *,
        allow_remote: bool = False,
    ) -> Server:
        """Start serving and return the underlying ``Server`` (does not block).

        Pass ``port=0`` to bind an ephemeral port (read it back from
        ``server.sockets[0].getsockname()[1]``). Rejects non-loopback ``host``
        unless ``allow_remote=True``.
        """

        self._validate_bind(host, allow_remote=allow_remote)
        self._closing = False
        self._server = await websockets.serve(
            self._connection_handler,
            host,
            port,
            process_request=self._process_request,
        )
        bound = ""
        if self._server.sockets:
            bound = str(self._server.sockets[0].getsockname())
        logger.info("ws_host listening on %s (requested %s:%s)", bound, host, port)
        return self._server

    async def serve(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        *,
        allow_remote: bool = False,
    ) -> None:
        """Start serving and block until :meth:`shutdown` is called."""

        server = await self.start(host, port, allow_remote=allow_remote)
        try:
            await server.wait_closed()
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Close active + queued connections (code 1001) and stop the server."""

        if self._closing:
            return
        self._closing = True

        if self._server is not None:
            self._server.close()

        closers: list[Awaitable[Any]] = []
        active = self._active
        if active is not None:
            closers.append(active.ws.close(_CLOSE_GOING_AWAY, "server shutdown"))
        for waiter in list(self._waiters):
            closers.append(waiter.ws.close(_CLOSE_GOING_AWAY, "server shutdown"))
        if closers:
            await asyncio.gather(*closers, return_exceptions=True)

        if self._server is not None:
            with contextlib.suppress(Exception):
                await self._server.wait_closed()

    # ------------------------------------------------------------------ #
    # Bind validation.
    # ------------------------------------------------------------------ #
    @staticmethod
    def _is_loopback(host: str) -> bool:
        if host in _LOOPBACK_HOSTNAMES:
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    def _validate_bind(self, host: str, *, allow_remote: bool) -> None:
        if self._is_loopback(host):
            return
        if allow_remote:
            logger.warning(
                "SECURITY: ws_host binding to NON-LOOPBACK address %r because "
                "allow_remote=True. The AutoCode WebSocket host has no auth and "
                "is intended for local-first use only. Exposing it to a network "
                "grants unauthenticated shell/tool access. You have been warned.",
                host,
            )
            return
        raise ValueError(
            f"Refusing to bind ws_host to non-loopback address {host!r}. "
            "The host is local-first and unauthenticated. Pass allow_remote=True "
            "to override (strongly discouraged)."
        )

    # ------------------------------------------------------------------ #
    # Connection acceptance / single-active + FIFO queue.
    # ------------------------------------------------------------------ #
    def _next_client_id(self, ws: ServerConnection) -> str:
        n = next(self._client_ids)
        try:
            peer = ws.remote_address
        except Exception:  # pragma: no cover - defensive
            peer = None
        return f"ws-{n}" if peer is None else f"ws-{n}@{peer[0]}:{peer[1]}"

    def _try_claim_active(self, client_id: str, ws: ServerConnection) -> Optional[_ActiveConn]:
        """Synchronously claim the active slot if free (no ``await`` inside)."""

        if self._active is not None:
            return None
        active = _ActiveConn(
            client_id=client_id,
            ws=ws,
            queue=asyncio.Queue(maxsize=self._queue_maxsize),
        )
        self._active = active
        return active

    async def _connection_handler(self, ws: ServerConnection) -> None:
        """websockets per-connection entry point."""

        client_id = self._next_client_id(ws)

        active = self._try_claim_active(client_id, ws)
        if active is not None:
            await self._serve_active(active)
            return

        # Slot busy -> queue behind the active client.
        waiter = _Waiter(client_id=client_id, ws=ws)
        self._waiters.append(waiter)
        position = len(self._waiters)
        await self._send_direct(
            ws,
            {
                "jsonrpc": "2.0",
                "method": "on_status",
                "params": {"queued": True, "position": position},
            },
        )

        await self._await_promotion_or_close(waiter)

        if waiter.active is not None:
            await self._serve_active(waiter.active)
        else:
            # Disconnected while queued; drop from the FIFO and renumber.
            self._drop_waiter(waiter)

    async def _await_promotion_or_close(self, waiter: _Waiter) -> None:
        promote_task = asyncio.ensure_future(waiter.promote_event.wait())
        closed_task = asyncio.ensure_future(waiter.ws.wait_closed())
        try:
            await asyncio.wait(
                {promote_task, closed_task}, return_when=asyncio.FIRST_COMPLETED
            )
        finally:
            for task in (promote_task, closed_task):
                if not task.done():
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task

    def _drop_waiter(self, waiter: _Waiter) -> None:
        with contextlib.suppress(ValueError):
            self._waiters.remove(waiter)
        self._renumber_waiters()

    def _renumber_waiters(self) -> None:
        """Best-effort re-broadcast of queue positions after the FIFO changes."""

        for index, waiter in enumerate(self._waiters, start=1):
            asyncio.ensure_future(
                self._send_direct(
                    waiter.ws,
                    {
                        "jsonrpc": "2.0",
                        "method": "on_status",
                        "params": {"queued": True, "position": index},
                    },
                )
            )

    # ------------------------------------------------------------------ #
    # Active connection: read loop + serialized writer.
    # ------------------------------------------------------------------ #
    async def _serve_active(self, active: _ActiveConn) -> None:
        writer_task = asyncio.ensure_future(self._writer_loop(active))
        try:
            async for raw in active.ws:
                await self._handle_inbound(active, raw)
        except ConnectionClosed:
            pass
        finally:
            await self._stop_writer(active, writer_task)
            self._release_and_promote(active)

    async def _writer_loop(self, active: _ActiveConn) -> None:
        """Single serialized writer for one active connection."""

        while True:
            item = await active.queue.get()
            try:
                if item is _WRITER_STOP:
                    return
                try:
                    await active.ws.send(json.dumps(item))
                except ConnectionClosed:
                    return
                except Exception:  # pragma: no cover - defensive
                    logger.exception("ws_host writer failed to send frame")
            finally:
                active.queue.task_done()

    async def _stop_writer(self, active: _ActiveConn, writer_task: asyncio.Task) -> None:
        # Ask the writer to drain and stop; fall back to cancel if it is wedged.
        with contextlib.suppress(asyncio.QueueFull):
            active.queue.put_nowait(_WRITER_STOP)
        try:
            await asyncio.wait_for(asyncio.shield(writer_task), timeout=2.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            writer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await writer_task

    def _release_and_promote(self, active: _ActiveConn) -> None:
        """Release the active slot and synchronously promote the next waiter.

        Runs with no ``await`` so no other coroutine can claim the freed slot in
        between (avoids two-active races).
        """

        if self._active is active:
            self._active = None

        while self._waiters:
            waiter = self._waiters.popleft()
            if waiter.ws.close_code is not None:
                # Waiter already gone; skip it.
                continue
            promoted = _ActiveConn(
                client_id=waiter.client_id,
                ws=waiter.ws,
                queue=asyncio.Queue(maxsize=self._queue_maxsize),
            )
            self._active = promoted
            waiter.active = promoted
            waiter.promote_event.set()
            break

        self._renumber_waiters()

    # ------------------------------------------------------------------ #
    # Inbound message handling.
    # ------------------------------------------------------------------ #
    async def _handle_inbound(self, active: _ActiveConn, raw: Any) -> None:
        try:
            message = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            await self._enqueue(active, _parse_error())
            return

        if not isinstance(message, dict):
            await self._enqueue(active, _invalid_request())
            return

        if "method" in message:
            response = await _maybe_await(
                self._app.dispatch_rpc_request(active.client_id, message)
            )
            if response is not None:
                await self._enqueue(active, response)
        elif "id" in message:
            # Response to a server-initiated request (approval / ask-user).
            await _maybe_await(
                self._app.route_rpc_response(active.client_id, message)
            )
        else:
            await self._enqueue(active, _invalid_request())

    # ------------------------------------------------------------------ #
    # Outbound seam (called by the app) + internal enqueue.
    # ------------------------------------------------------------------ #
    async def emit_response(self, client_id: str, message: dict[str, Any]) -> None:
        """Outbound push used by the app for notifications, server-initiated
        requests, and responses. Routed through the active connection's
        serialized writer queue (back-pressure via bounded queue).

        Drops silently (debug log) if ``client_id`` is not the active client --
        e.g. the client disconnected mid-turn.
        """

        active = self._active
        if active is None or active.client_id != client_id:
            logger.debug(
                "ws_host: dropping outbound frame for inactive client %r", client_id
            )
            return
        await self._enqueue(active, message)

    async def _enqueue(self, active: _ActiveConn, message: dict[str, Any]) -> None:
        await active.queue.put(message)

    async def _send_direct(self, ws: ServerConnection, message: dict[str, Any]) -> None:
        """Send a frame directly (used for queued connections that have no
        serialized writer task)."""

        with contextlib.suppress(ConnectionClosed):
            await ws.send(json.dumps(message))

    # ------------------------------------------------------------------ #
    # Static file serving (HTTP GET on the same port).
    # ------------------------------------------------------------------ #
    async def _process_request(
        self, connection: ServerConnection, request: Request
    ) -> Optional[Response]:
        """websockets pre-handshake hook.

        Returns ``None`` for WebSocket upgrade requests (proceed to handshake),
        otherwise serves a static file (or 404).
        """

        upgrade = request.headers.get("Upgrade", "")
        if upgrade and "websocket" in upgrade.lower():
            return None

        if self._static_dir is None:
            return connection.respond(HTTPStatus.NOT_FOUND, "Not Found\n")

        resolved = self._resolve_static_path(request.path)
        if resolved is None:
            return connection.respond(HTTPStatus.NOT_FOUND, "Not Found\n")

        body = resolved.read_bytes()
        ctype = _content_type_for(resolved)
        headers = Headers(
            [
                ("Content-Type", ctype),
                ("Content-Length", str(len(body))),
            ]
        )
        return Response(HTTPStatus.OK, HTTPStatus.OK.phrase, headers, body)

    def _resolve_static_path(self, request_path: str) -> Optional[Path]:
        """Map an HTTP request path to a file inside ``static_dir``.

        Returns ``None`` if static serving is disabled, the path escapes the
        directory (traversal), or the target is missing / not a regular file.
        """

        if self._static_dir is None:
            return None

        # Strip query string / fragment.
        path = request_path.split("?", 1)[0].split("#", 1)[0]
        # URL-decode percent escapes so encoded traversal is also caught.
        from urllib.parse import unquote

        path = unquote(path)
        if path in ("", "/"):
            path = "/index.html"

        relative = path.lstrip("/")
        candidate = (self._static_dir / relative).resolve()

        # Prefix check: candidate must live within static_dir.
        if candidate != self._static_dir and self._static_dir not in candidate.parents:
            return None
        if not candidate.is_file():
            return None
        return candidate


# --------------------------------------------------------------------------- #
# JSON-RPC error helpers.
# --------------------------------------------------------------------------- #
def _parse_error() -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "error": {"code": -32700, "message": "Parse error"},
        "id": None,
    }


def _invalid_request() -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "error": {"code": -32600, "message": "Invalid Request"},
        "id": None,
    }


def _content_type_for(path: Path) -> str:
    # Ensure common web types resolve even if the OS mime registry is sparse.
    overrides = {
        ".js": "text/javascript; charset=utf-8",
        ".mjs": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".htm": "text/html; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".svg": "image/svg+xml",
        ".map": "application/json; charset=utf-8",
    }
    suffix = path.suffix.lower()
    if suffix in overrides:
        return overrides[suffix]
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "application/octet-stream"


# --------------------------------------------------------------------------- #
# Demo standalone app + main().
# --------------------------------------------------------------------------- #
class _EchoApp:
    """Trivial ``RpcApplication`` for the standalone demo.

    Echoes ``chat`` requests, streams a couple of ``on_token`` notifications,
    and demonstrates a server-initiated ``on_tool_request`` round-trip.
    """

    def __init__(self) -> None:
        self._host: Optional[WsHost] = None
        self._pending: dict[str, str] = {}
        self._counter = itertools.count(1)

    def attach_transport(self, host: WsHost) -> None:
        self._host = host

    async def dispatch_rpc_request(
        self, client_id: str, message: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        method = message.get("method")
        msg_id = message.get("id")

        if method == "chat" and self._host is not None:
            text = str(message.get("params", {}).get("text", ""))
            for i, chunk in enumerate((text or "hello").split()):
                await self._host.emit_response(
                    client_id,
                    {
                        "jsonrpc": "2.0",
                        "method": "on_token",
                        "params": {"index": i, "text": chunk + " "},
                    },
                )
            await self._host.emit_response(
                client_id,
                {"jsonrpc": "2.0", "method": "on_done", "params": {"cancelled": False}},
            )

        if msg_id is None:
            return None  # notification -> no response
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"ok": True, "echo": method}}

    def route_rpc_response(self, client_id: str, message: dict[str, Any]) -> None:
        logger.info("demo: client %s replied to request: %s", client_id, message)
        self._pending.pop(str(message.get("id")), None)


def _default_static_dir() -> Path:
    """The WebUI directory is the parent of this file's directory."""

    return Path(__file__).resolve().parent.parent


async def _amain(args: argparse.Namespace) -> None:
    logging.basicConfig(level=logging.INFO)
    app = _EchoApp()
    static_dir = None if args.no_static else Path(args.static_dir)
    host = WsHost(app, static_dir=static_dir)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signame in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, signame, None)
        if sig is not None:
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, stop.set)

    server = await host.start(args.host, args.port, allow_remote=args.allow_remote)
    port = server.sockets[0].getsockname()[1] if server.sockets else args.port
    logger.info("demo ws_host up: ws://%s:%s (static=%s)", args.host, port, static_dir)
    try:
        await stop.wait()
    finally:
        await host.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="AutoCode WebSocket host (demo)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--static-dir",
        default=str(_default_static_dir()),
        help="Directory served over HTTP GET (defaults to the webui/ dir).",
    )
    parser.add_argument("--no-static", action="store_true", help="Disable static serving.")
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Allow non-loopback bind (UNSAFE, no auth).",
    )
    args = parser.parse_args()
    try:
        asyncio.run(_amain(args))
    except KeyboardInterrupt:  # pragma: no cover
        pass


if __name__ == "__main__":
    main()
