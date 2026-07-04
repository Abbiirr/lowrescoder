# /// script
# requires-python = ">=3.11"
# dependencies = ["websockets>=12"]
# ///
"""
ws-bridge.py — connect the browser WebUI to the REAL AutoCode backend.

The browser can't speak the backend's raw TCP JSON-RPC transport, so this process
sits in the middle: it accepts a WebSocket connection from the WebUI (and can serve
the UI files over HTTP on the same port), opens a TCP connection to a running
`autocode serve --transport tcp`, and forwards JSON-RPC frames verbatim in both
directions. It does NOT interpret the protocol — it only reframes.

    browser  <--WebSocket-->  ws-bridge  <--TCP-->  autocode serve --transport tcp

Run:
    # terminal 1 — the real backend (from the real autocode checkout):
    uv run autocode serve --transport tcp --host 127.0.0.1 --port 8790
    # terminal 2 — the bridge (from this repo):
    uv run --no-project webui/ws-bridge.py --backend-port 8790
    # then open the printed UI_URL

VERIFY against the real backend before relying on this (see REAL-HARNESS.md):
  * --framing: how the TCP transport delimits messages. Default is newline-delimited
    JSON (NDJSON). If the real host uses LSP-style `Content-Length:` headers, pass
    `--framing lsp`. Confirm against `autocode/src/autocode/backend/tcp_host.py` and
    the `rpc-schema-v1` fixtures.
  * The WebUI expects the documented notification names (on_token, on_tool_call,
    on_tool_request, ...) and the server-initiated approval request path. Those are the
    backend's own contract (agent-events.md), so a conformant backend already matches;
    the bridge just passes them through.
"""
from __future__ import annotations

import argparse
import asyncio
import mimetypes
import sys
from http import HTTPStatus
from pathlib import Path
from urllib.parse import unquote

import websockets

try:
    from websockets.datastructures import Headers as _Headers
    from websockets.http11 import Response as _Response
    _STATIC_OK = True
except Exception:  # pragma: no cover
    _STATIC_OK = False

_STATIC_DIR: Path | None = None
_ACTIVE = False

_CTYPES = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml", ".ico": "image/x-icon",
}


def _content_type(path: Path) -> str:
    return _CTYPES.get(path.suffix.lower()) or (mimetypes.guess_type(str(path))[0] or "application/octet-stream")


def _resolve_static(request_path: str) -> Path | None:
    if _STATIC_DIR is None:
        return None
    p = unquote(request_path.split("?", 1)[0].split("#", 1)[0])
    if p in ("", "/"):
        p = "/index.html"
    cand = (_STATIC_DIR / p.lstrip("/")).resolve()
    if cand != _STATIC_DIR and _STATIC_DIR not in cand.parents:
        return None
    return cand if cand.is_file() else None


def _process_request(connection, request):
    if (request.headers.get("Upgrade") or "").lower() == "websocket":
        return None
    if not _STATIC_OK or _STATIC_DIR is None:
        return connection.respond(HTTPStatus.NOT_FOUND, "Not Found\n")
    target = _resolve_static(request.path)
    if target is None:
        return connection.respond(HTTPStatus.NOT_FOUND, "Not Found\n")
    body = target.read_bytes()
    headers = _Headers([("Content-Type", _content_type(target)), ("Content-Length", str(len(body)))])
    return _Response(HTTPStatus.OK, HTTPStatus.OK.phrase, headers, body)


# ---------------- TCP framing (VERIFY against the real transport) ----------------

async def read_framed(reader: asyncio.StreamReader, framing: str) -> bytes | None:
    """Read one JSON-RPC message from the backend TCP stream."""
    if framing == "lsp":
        # LSP-style: `Content-Length: N\r\n\r\n<body>`
        headers = {}
        while True:
            line = await reader.readline()
            if not line:
                return None
            line = line.strip()
            if not line:
                break
            if b":" in line:
                k, _, v = line.partition(b":")
                headers[k.strip().lower()] = v.strip()
        n = int(headers.get(b"content-length", b"0"))
        return await reader.readexactly(n) if n else b""
    # default: newline-delimited JSON (NDJSON)
    line = await reader.readline()
    if not line:
        return None
    return line.rstrip(b"\r\n")


def frame(payload: bytes, framing: str) -> bytes:
    if framing == "lsp":
        return b"Content-Length: %d\r\n\r\n%s" % (len(payload), payload)
    return payload + b"\n"


# ---------------- bridge ----------------

async def bridge_connection(ws, backend_host: str, backend_port: int, framing: str) -> None:
    try:
        reader, writer = await asyncio.open_connection(backend_host, backend_port)
    except OSError as e:
        print(f"[bridge] backend unreachable at {backend_host}:{backend_port} ({e})", flush=True)
        await ws.close(code=1011, reason="backend unreachable")
        return
    print(f"[bridge] client <-> backend {backend_host}:{backend_port} ({framing})", flush=True)

    async def ws_to_tcp():
        try:
            async for msg in ws:
                data = msg.encode("utf-8") if isinstance(msg, str) else msg
                writer.write(frame(data, framing))
                await writer.drain()
        except Exception:
            pass
        finally:
            with_suppress(writer.close)

    async def tcp_to_ws():
        try:
            while True:
                payload = await read_framed(reader, framing)
                if payload is None:
                    break
                if payload == b"":
                    continue
                await ws.send(payload.decode("utf-8"))
        except Exception:
            pass

    t1 = asyncio.create_task(ws_to_tcp())
    t2 = asyncio.create_task(tcp_to_ws())
    done, pending = await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
    for t in pending:
        t.cancel()
    with_suppress(writer.close)
    with_suppress(ws.close)


def with_suppress(fn):
    try:
        r = fn()
        if asyncio.iscoroutine(r):
            asyncio.ensure_future(r)
    except Exception:
        pass


def make_handler(backend_host: str, backend_port: int, framing: str, single: bool):
    async def handler(ws, *_a):
        global _ACTIVE
        if single and _ACTIVE:
            await ws.close(code=1013, reason="bridge busy")
            return
        _ACTIVE = True
        try:
            await bridge_connection(ws, backend_host, backend_port, framing)
        finally:
            _ACTIVE = False
    return handler


async def main() -> None:
    global _STATIC_DIR
    ap = argparse.ArgumentParser(description="WebSocket<->TCP JSON-RPC bridge for the AutoCode WebUI.")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8901, help="WS/UI port for the browser (falls back to ephemeral).")
    ap.add_argument("--backend-host", default="127.0.0.1")
    ap.add_argument("--backend-port", type=int, required=True, help="Port of `autocode serve --transport tcp`.")
    ap.add_argument("--framing", choices=["newline", "lsp"], default="newline", help="TCP message framing (VERIFY).")
    ap.add_argument("--no-ui", action="store_true", help="Do not serve the WebUI files over HTTP.")
    ap.add_argument("--max-seconds", type=float, default=0.0)
    ap.add_argument("--single", action="store_true", help="Allow only one browser connection at a time.")
    args = ap.parse_args()

    if args.host not in ("127.0.0.1", "localhost", "::1"):
        print(f"[bridge] refusing non-loopback host {args.host!r}", file=sys.stderr)
        sys.exit(2)
    if not args.no_ui and _STATIC_OK:
        _STATIC_DIR = Path(__file__).resolve().parent
    serve_kw = {"process_request": _process_request} if _STATIC_DIR is not None else {}

    handler = make_handler(args.backend_host, args.backend_port, args.framing, args.single)
    try:
        server = await websockets.serve(handler, args.host, args.port, **serve_kw)
    except OSError as e:
        print(f"[bridge] port {args.port} unavailable ({e.errno}); using an ephemeral port", flush=True)
        server = await websockets.serve(handler, args.host, 0, **serve_kw)

    bound = server.sockets[0].getsockname()[1] if server.sockets else args.port
    print(f"[bridge] listening on ws://{args.host}:{bound} -> backend tcp://{args.backend_host}:{args.backend_port}", flush=True)
    if _STATIC_DIR is not None:
        print(f"UI_URL http://{args.host}:{bound}/index.html?live=1", flush=True)
    try:
        if args.max_seconds > 0:
            await asyncio.sleep(args.max_seconds)
        else:
            await asyncio.Future()
    finally:
        server.close()
        await server.wait_closed()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
