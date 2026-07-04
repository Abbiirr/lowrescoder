# /// script
# requires-python = ">=3.11"
# dependencies = ["websockets>=12"]
# ///
"""
mock-server.py — protocol-conformant mock of the AutoCode harness backend.

Run:  uv run --no-project webui/mock-server.py [--port 8901]

Emulates the documented JSON-RPC surface (docs/features/backend_features.md,
docs/features/agent-events.md) so the WebUI can be developed and verified without
the real backend (whose sources are absent from this checkout). Loopback only,
single active client. Every inbound/outbound frame is logged to stdout.

Scope of fidelity — see webui/test-results/*-t1.md "Protocol assumptions":
  * request methods answered with plausible fixtures
  * `chat` streams a scripted turn: ack -> thinking -> tokens -> tool_calls ->
    SERVER-INITIATED on_tool_request (awaits the client's response) -> (approved)
    more tokens + cost + done, or (denied/cancelled) done.
  * on_tool_request / on_ask_user are server-initiated JSON-RPC *requests* (id +
    method); the client replies with a JSON-RPC *response* carrying the decision.
"""
from __future__ import annotations

import argparse
import asyncio
import itertools
import json
import mimetypes
import sys
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from urllib.parse import unquote

import websockets

# Static-serving (new asyncio API) is optional: if these symbols are missing the
# server still works over WebSocket, it just won't host the UI over HTTP.
try:
    from websockets.datastructures import Headers as _Headers
    from websockets.http11 import Response as _Response
    _STATIC_OK = True
except Exception:  # pragma: no cover - depends on websockets version
    _STATIC_OK = False

_active_client = False           # single-active-client guard
_STATIC_DIR: Path | None = None  # set in main() when UI hosting is enabled

_CTYPES = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml", ".ico": "image/x-icon", ".map": "application/json; charset=utf-8",
}


def _content_type(path: Path) -> str:
    return _CTYPES.get(path.suffix.lower()) or (mimetypes.guess_type(str(path))[0] or "application/octet-stream")


def _resolve_static(request_path: str) -> Path | None:
    if _STATIC_DIR is None:
        return None
    path = unquote(request_path.split("?", 1)[0].split("#", 1)[0])
    if path in ("", "/"):
        path = "/index.html"
    candidate = (_STATIC_DIR / path.lstrip("/")).resolve()
    if candidate != _STATIC_DIR and _STATIC_DIR not in candidate.parents:
        return None  # traversal
    return candidate if candidate.is_file() else None


def _process_request(connection, request):
    """Pre-handshake hook: pass WebSocket upgrades through, otherwise serve a file."""
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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str = "ev") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def log(direction: str, obj) -> None:
    try:
        s = json.dumps(obj)
    except Exception:
        s = str(obj)
    if len(s) > 240:
        s = s[:237] + "..."
    print(f"[mock] {direction} {s}", flush=True)


# ---------------- fixtures ----------------

SESSIONS = [
    {"id": "s1", "title": "Fix booking double-charge on overlap", "meta": "worktree · AC-1 High · running 4m", "group": "active", "running": True, "badge": "Needs approval", "badgeKind": "warn"},
    {"id": "s3", "title": "Migrate booking store to Zustand", "meta": "cloud · AC-1 Fast · running 12m", "group": "active", "running": True},
    {"id": "s2", "title": "Pricing calculator: member discounts", "meta": "worktree · merged 1h ago", "group": "recent", "done": True, "badge": "PR #128", "badgeKind": "ok"},
    {"id": "s4", "title": "Dark mode for kiosk check-in", "meta": "local · yesterday", "group": "recent", "done": True},
    {"id": "s5", "title": "Weekly dependency audit", "meta": "automation · Mon 09:00", "group": "recent", "done": True, "badge": "Auto", "badgeKind": "dim"},
]
MODELS = [
    {"label": "AC-1 High", "desc": "Deep reasoning for gnarly work"},
    {"label": "AC-1 Fast", "desc": "Everyday edits and reviews"},
    {"label": "AC-mini", "desc": "Cheap bulk tasks"},
]
PROVIDERS = [{"label": "ollama"}, {"label": "openrouter"}]
COMMANDS = [
    {"cmd": "/review", "desc": "Audit the current diff for risky changes and missing tests"},
    {"cmd": "/test", "desc": "Write or update tests for the selected code path"},
    {"cmd": "/fix-ci", "desc": "Pull the latest CI failure and fix it"},
    {"cmd": "/explain", "desc": "Explain the selected code with references"},
    {"cmd": "/commit", "desc": "Stage, write a conventional commit, and push"},
]


class Client:
    """Per-connection state + JSON-RPC plumbing."""

    def __init__(self, ws):
        self.ws = ws
        self.srv_ids = itertools.count(1)         # ids for server-initiated requests
        self.pending: dict = {}                   # srv_id -> Future (awaiting client response)
        self.cancel = asyncio.Event()
        self.chat_task: asyncio.Task | None = None
        self.session_id = "s1"
        self.model = "AC-1 High"
        self.provider = "ollama"
        self.mode = "Worktree"

    async def send(self, obj) -> None:
        log("->", obj)
        await self.ws.send(json.dumps(obj))

    async def notify(self, method: str, params: dict) -> None:
        params = dict(params)
        params.setdefault("id", new_id())
        params.setdefault("sessionId", self.session_id)
        params.setdefault("timestamp", now_iso())
        await self.send({"jsonrpc": "2.0", "method": method, "params": params})

    async def server_request(self, method: str, params: dict):
        """Send a server-initiated request and await the client's response."""
        sid = next(self.srv_ids)
        params = dict(params)
        params.setdefault("id", new_id("req"))
        params.setdefault("sessionId", self.session_id)
        params.setdefault("timestamp", now_iso())
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self.pending[sid] = fut
        await self.send({"jsonrpc": "2.0", "id": sid, "method": method, "params": params})
        return fut

    def resolve_response(self, msg: dict) -> None:
        fut = self.pending.pop(msg.get("id"), None)
        if fut and not fut.done():
            if "error" in msg and msg["error"]:
                fut.set_result({"decision": "deny", "error": msg["error"]})
            else:
                fut.set_result(msg.get("result") or {})

    # ---------------- request dispatch ----------------

    async def handle_request(self, msg: dict) -> None:
        method = msg.get("method")
        params = msg.get("params") or {}
        rid = msg.get("id")

        result, err = await self.dispatch(method, params)
        if rid is not None:  # request (not a notification) -> respond
            if err is not None:
                await self.send({"jsonrpc": "2.0", "id": rid, "error": err})
            else:
                await self.send({"jsonrpc": "2.0", "id": rid, "result": result})

    async def dispatch(self, method: str, params: dict):
        if method == "session.list":
            return {"sessions": SESSIONS}, None
        if method == "session.new":
            self.session_id = new_id("s")
            return {"session_id": self.session_id}, None
        if method == "session.resume":
            self.session_id = params.get("session_id") or params.get("id") or self.session_id
            return {"session_id": self.session_id, "transcript": []}, None
        if method == "session.fork":
            return {"session_id": new_id("s"), "parent_session_id": self.session_id}, None
        if method == "model.list":
            return {"models": MODELS}, None
        if method == "provider.list":
            return {"providers": PROVIDERS}, None
        if method in ("command.list",):
            return {"commands": COMMANDS}, None
        if method == "task.list":
            return {"tasks": []}, None
        if method == "subagent.list":
            return {"subagents": []}, None
        if method in ("plan.status",):
            return {"plan": None}, None
        if method == "config.get":
            return {"model": self.model, "provider": self.provider, "mode": self.mode}, None
        if method == "config.set":
            for k in ("model", "provider", "mode"):
                if k in params:
                    setattr(self, k, params[k])
            await self.notify("on_status", {"model": self.model, "provider": self.provider, "mode": self.mode, "session_id": self.session_id})
            return {"ok": True}, None
        if method in ("memory.list", "checkpoint.list"):
            return {"items": []}, None
        if method == "cancel":
            self.cancel.set()
            return {"ok": True}, None
        if method == "steer":
            return {"ok": True}, None
        if method == "command":
            # Treat a slash command like a chat prompt.
            asyncio.create_task(self.run_chat_turn(params.get("command") or params.get("name") or ""))
            return {"ok": True}, None
        if method == "chat":
            prompt = params.get("text") or params.get("prompt") or params.get("message") or ""
            self.cancel = asyncio.Event()
            self.chat_task = asyncio.create_task(self.run_chat_turn(prompt))
            return {"ok": True, "session_id": self.session_id}, None
        if method == "shutdown":
            return {"ok": True}, None
        return None, {"code": -32601, "message": f"method not found: {method}"}

    # ---------------- scripted chat turn ----------------

    async def _beat(self, secs: float) -> bool:
        """Sleep unless cancelled. Returns True if cancelled."""
        try:
            await asyncio.wait_for(self.cancel.wait(), timeout=secs)
            return True
        except asyncio.TimeoutError:
            return False

    async def run_chat_turn(self, prompt: str) -> None:
        try:
            await self.notify("on_chat_ack", {"text": prompt, "session_id": self.session_id, "model": self.model, "mode": self.mode})
            await self.notify("on_status", {"model": self.model, "provider": self.provider, "mode": self.mode, "session_id": self.session_id})

            await self.notify("on_thinking", {"status": "running", "text": "Analyzing the request"})
            if await self._beat(0.15):
                return await self.finish(cancelled=True)

            # streamed answer (first half) — each token is a distinct event (unique id);
            # the reducer groups tokens by the in-progress answer row, not by id.
            for chunk in ["Looking at the booking charge path. ", "splitAtClose() keeps full duration on both halves, ", "so calcTotal bills the spanning block twice.\n\n"]:
                if self.cancel.is_set():
                    return await self.finish(cancelled=True)
                await self.notify("on_token", {"id": new_id("tok"), "text": chunk})
                await self._beat(0.05)

            # tool call: read files (pending -> running -> done)
            call1 = new_id("call")
            await self.notify("on_tool_call", {"id": call1, "callId": call1, "type": "ToolStartEvent", "tool": "read_file", "title": "Read 3 files", "status": "pending"})
            await self._beat(0.05)
            await self.notify("on_tool_call", {"id": new_id(), "callId": call1, "type": "ToolStartEvent", "tool": "read_file", "status": "running"})
            await self._beat(0.08)
            await self.notify("on_tool_call", {"id": new_id(), "callId": call1, "type": "ToolResultEvent", "status": "done", "meta": "12.4k tokens",
                                               "result": {"files": ["src/stores/bookingStore.ts — 212 lines", "src/lib/pricing.ts — 84 lines", "src/lib/sessions.ts — 141 lines"]}})

            # tool call: run tests (fails)
            call2 = new_id("call")
            await self.notify("on_tool_call", {"id": call2, "callId": call2, "type": "ToolStartEvent", "tool": "run_command", "title": "pnpm vitest run pricing", "status": "running"})
            if await self._beat(0.1):
                return await self.finish(cancelled=True)
            await self.notify("on_tool_call", {"id": new_id(), "callId": call2, "type": "ToolResultEvent", "status": "failed", "meta": "2 failed",
                                               "result": {"ok": False, "output": "✗ charges once when session spans close\n    expected 2400 to equal 1200\n\nTests  2 failed | 6 passed (8)"}})

            await self.notify("on_thinking", {"status": "done"})

            # server-initiated approval request (command matches the UI's demo card)
            fut = await self.server_request("on_tool_request", {
                "title": "Approval needed",
                "tool": "run_command",
                "command": 'pnpm test:e2e --grep "booking overlap"',
                "detail": "Command runs outside the sandbox — needs network for the payment fixture",
            })
            done, _pending = await asyncio.wait({asyncio.ensure_future(fut), asyncio.ensure_future(self.cancel.wait())}, return_when=asyncio.FIRST_COMPLETED)
            if self.cancel.is_set():
                return await self.finish(cancelled=True)
            decision = (fut.result() if fut.done() else {}) or {}
            allow = decision.get("decision") in (None, "allow", "approve", "allow_once", "yes")

            if allow:
                call3 = new_id("call")
                await self.notify("on_tool_call", {"id": call3, "callId": call3, "type": "ToolStartEvent", "tool": "run_command", "title": "pnpm test:e2e", "status": "running"})
                await self._beat(0.1)
                await self.notify("on_tool_call", {"id": new_id(), "callId": call3, "type": "ToolResultEvent", "status": "done", "meta": "4 passed",
                                                   "result": {"output": "4 passed (4)  ·  11.2s"}})
                await self.notify("on_token", {"id": new_id("tok"), "text": "Fixed: calcTotal now clamps chargeable time at venue close and credits the overlap once. All tests green."})
            else:
                await self.notify("on_token", {"id": new_id("tok"), "text": "Skipped the e2e run per your choice. The unit-level fix still stands; re-run when ready."})

            await self.notify("on_cost_update", {"cost": 0.42, "tokens_in": 12400, "tokens_out": 860, "pct": 64})
            await self.finish(cancelled=False)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # never crash the connection on a scripting bug
            log("!!", {"chat_error": str(e)})
            await self.notify("on_error", {"message": f"mock turn error: {e}"})

    async def finish(self, cancelled: bool) -> None:
        await self.notify("on_done", {"tokens_in": 12400, "tokens_out": 860, "layer_used": 4, "cancelled": cancelled, "model": self.model})


async def handler(ws, *_args):
    global _active_client
    if _active_client:
        log("xx", {"rejected": "single active client"})
        await ws.close(code=1013, reason="server busy (single active client)")
        return
    _active_client = True
    client = Client(ws)
    log("++", {"client": "connected"})
    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except Exception:
                await client.send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
                continue
            log("<-", msg)
            if not isinstance(msg, dict):
                continue
            # response to a server-initiated request?
            if "id" in msg and "method" not in msg:
                client.resolve_response(msg)
                continue
            # request or notification
            asyncio.create_task(client.handle_request(msg))
    except websockets.ConnectionClosed:
        pass
    finally:
        _active_client = False
        if client.chat_task and not client.chat_task.done():
            client.chat_task.cancel()
        log("--", {"client": "disconnected"})


async def main() -> None:
    global _STATIC_DIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8901)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--max-seconds", type=float, default=0.0,
                    help="watchdog: exit after N seconds (0 = run forever). Guards against orphaned test servers.")
    ap.add_argument("--no-ui", action="store_true", help="Do not serve the WebUI files over HTTP.")
    args = ap.parse_args()
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        print(f"[mock] refusing non-loopback host {args.host!r}", file=sys.stderr)
        sys.exit(2)

    if not args.no_ui and _STATIC_OK:
        _STATIC_DIR = Path(__file__).resolve().parent  # the webui/ directory
    serve_kw = {"process_request": _process_request} if _STATIC_DIR is not None else {}

    # Bind the requested port; fall back to an OS-assigned port if it's unavailable
    # (Windows reserves ranges — e.g. Hyper-V/WinNAT — so a fixed port may be excluded).
    try:
        server = await websockets.serve(handler, args.host, args.port, **serve_kw)
    except OSError as e:
        print(f"[mock] port {args.port} unavailable ({e.errno}); using an ephemeral port", flush=True)
        server = await websockets.serve(handler, args.host, 0, **serve_kw)

    bound = server.sockets[0].getsockname()[1] if server.sockets else args.port
    print(f"[mock] listening on ws://{args.host}:{bound}", flush=True)
    if _STATIC_DIR is not None:
        # Machine-readable line the launcher parses to open the browser at the real port.
        print(f"UI_URL http://{args.host}:{bound}/index.html?live=1", flush=True)
    try:
        if args.max_seconds > 0:
            await asyncio.sleep(args.max_seconds)
            print("[mock] watchdog timeout — exiting", flush=True)
        else:
            await asyncio.Future()  # run forever
    finally:
        server.close()
        await server.wait_closed()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
