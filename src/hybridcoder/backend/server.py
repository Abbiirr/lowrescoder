"""JSON-RPC backend server for the Go Bubble Tea TUI frontend.

Communicates via newline-delimited JSON-RPC 2.0 over stdin/stdout.
Mirrors the InlineApp agent loop but exposes it via RPC instead of a
prompt_toolkit UI.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

from hybridcoder.agent.approval import ApprovalManager, ApprovalMode
from hybridcoder.agent.loop import AgentLoop
from hybridcoder.agent.tools import ToolRegistry, create_default_registry
from hybridcoder.config import HybridCoderConfig, load_config
from hybridcoder.layer4.llm import create_provider
from hybridcoder.session.store import SessionStore
from hybridcoder.tui.commands import CommandRouter, create_default_router

logger = logging.getLogger(__name__)

# Python->Go request IDs start at 1000 to avoid collision with Go->Python IDs.
_PYTHON_REQUEST_ID_START = 1000


class _ServerAppContext:
    """Minimal adapter implementing the AppContext protocol for slash commands.

    Routes UI operations to JSON-RPC notifications so the Go frontend can
    display them.
    """

    def __init__(self, server: BackendServer) -> None:
        self._server = server

    @property
    def session_store(self) -> SessionStore:
        return self._server.session_store

    @property
    def session_id(self) -> str:
        return self._server.session_id

    @session_id.setter
    def session_id(self, value: str) -> None:
        self._server.session_id = value

    @property
    def config(self) -> HybridCoderConfig:
        return self._server.config

    @property
    def project_root(self) -> Path:
        return self._server.project_root

    @property
    def command_router(self) -> CommandRouter:
        return self._server.command_router

    @property
    def approval_mode(self) -> str:
        if self._server._approval_manager:
            return self._server._approval_manager.mode.value
        return self._server.config.tui.approval_mode

    @approval_mode.setter
    def approval_mode(self, value: str) -> None:
        self._server.config.tui.approval_mode = value  # type: ignore[assignment]
        mode = ApprovalMode(value)
        if self._server._approval_manager:
            self._server._approval_manager.mode = mode
        self._server._emit_status()

    @property
    def shell_enabled(self) -> bool:
        return self._server.config.shell.enabled

    @shell_enabled.setter
    def shell_enabled(self, value: bool) -> None:
        self._server.config.shell.enabled = value
        if self._server._approval_manager:
            self._server._approval_manager.shell_config.enabled = value

    @property
    def show_thinking(self) -> bool:
        return self._server._show_thinking

    @show_thinking.setter
    def show_thinking(self, value: bool) -> None:
        self._server._show_thinking = value

    def add_system_message(self, content: str) -> None:
        self._server.emit_notification("on_token", {"text": f"\n[System] {content}\n"})

    def clear_messages(self) -> None:
        self._server.emit_notification("on_token", {"text": "\n--- (cleared) ---\n"})

    def display_messages(self, messages: list[Any]) -> None:
        for msg in messages:
            text = f"[{msg.role}] {msg.content}\n"
            self._server.emit_notification("on_token", {"text": text})

    def get_assistant_messages(self) -> list[str]:
        messages = self._server.session_store.get_messages(self._server.session_id)
        return [m.content for m in messages if m.role == "assistant"]

    def copy_to_clipboard(self, text: str) -> bool:
        from hybridcoder.tui.commands import _copy_to_clipboard

        return _copy_to_clipboard(text)

    def exit_app(self) -> None:
        self._server._running = False


class BackendServer:
    """JSON-RPC server that manages the agent loop and communicates with Go TUI."""

    def __init__(
        self,
        config: HybridCoderConfig | None = None,
        project_root: Path | None = None,
    ) -> None:
        self.config = config or load_config()
        self.project_root = project_root or Path.cwd()

        # Session
        db_path = Path(self.config.tui.session_db_path).expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_store = SessionStore(str(db_path))

        self.session_id = self.session_store.create_session(
            title="New session",
            model=self.config.llm.model,
            provider=self.config.llm.provider,
            project_dir=str(self.project_root),
        )

        # Commands
        self.command_router: CommandRouter = create_default_router()
        self._app_context = _ServerAppContext(self)

        # Agent (lazy init)
        self._provider: Any = None
        self._tool_registry: ToolRegistry | None = None
        self._approval_manager: ApprovalManager | None = None
        self._agent_loop: AgentLoop | None = None
        self._agent_task: asyncio.Task[None] | None = None
        self._session_titled: bool = False

        # Thinking visibility
        self._show_thinking: bool = False

        # Session-level auto-approve tracking
        self._session_approved_tools: set[str] = set()

        # Stats
        self._total_tokens_in: int = 0
        self._total_tokens_out: int = 0
        self._edit_count: int = 0

        # Wire protocol state
        self._next_request_id: int = _PYTHON_REQUEST_ID_START
        self._pending_futures: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._running: bool = True
        self._writer: asyncio.StreamWriter | None = None

    # --- Wire protocol ---

    def emit_notification(self, method: str, params: dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no ID) to the Go frontend."""
        msg = {"jsonrpc": "2.0", "method": method, "params": params}
        self._write_message(msg)

    def emit_response(self, request_id: int, result: Any) -> None:
        """Send a JSON-RPC response to a Go->Python request."""
        msg = {"jsonrpc": "2.0", "id": request_id, "result": result}
        self._write_message(msg)

    async def emit_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC request to the Go frontend and wait for the response."""
        request_id = self._next_request_id
        self._next_request_id += 1

        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending_futures[request_id] = future

        msg = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }
        self._write_message(msg)

        try:
            return await future
        finally:
            self._pending_futures.pop(request_id, None)

    def _write_message(self, msg: dict[str, Any]) -> None:
        """Write a JSON message to stdout (newline-delimited)."""
        line = json.dumps(msg, separators=(",", ":")) + "\n"
        sys.stdout.write(line)
        sys.stdout.flush()

    def _emit_status(self) -> None:
        """Emit current status to the frontend."""
        mode = self.config.tui.approval_mode
        if self._approval_manager:
            mode = self._approval_manager.mode.value
        self.emit_notification("on_status", {
            "model": self.config.llm.model,
            "provider": self.config.llm.provider,
            "mode": mode,
            "session_id": self.session_id,
        })

    # --- Agent loop setup (mirrors InlineApp._ensure_agent_loop) ---

    def _ensure_agent_loop(self) -> AgentLoop:
        """Lazy-initialize agent loop with all dependencies."""
        if self._agent_loop is None:
            self._provider = create_provider(self.config)
            self._tool_registry = create_default_registry(
                project_root=str(self.project_root),
            )
            self._approval_manager = ApprovalManager(
                mode=ApprovalMode(self.config.tui.approval_mode),
                shell_config=self.config.shell,
            )

            # Load project memory if available
            memory_path = self.project_root / ".hybridcoder" / "memory.md"
            memory_content = None
            if memory_path.exists():
                try:
                    memory_content = memory_path.read_text(encoding="utf-8")
                except OSError:
                    pass

            self._agent_loop = AgentLoop(
                provider=self._provider,
                tool_registry=self._tool_registry,
                approval_manager=self._approval_manager,
                session_store=self.session_store,
                session_id=self.session_id,
                memory_content=memory_content,
            )

        return self._agent_loop

    # --- Agent loop callbacks (map to JSON-RPC) ---

    def _on_chunk(self, text: str) -> None:
        """Stream token callback -> notification on_token."""
        self.emit_notification("on_token", {"text": text})

    def _on_thinking_chunk(self, text: str) -> None:
        """Thinking token callback -> notification on_thinking."""
        self.emit_notification("on_thinking", {"text": text})

    def _on_tool_call(self, tool_name: str, status: str, result: str = "") -> None:
        """Tool call status callback -> notification on_tool_call."""
        self.emit_notification("on_tool_call", {
            "name": tool_name,
            "status": status,
            "result": result,
        })
        # Track edits
        if status in ("completed", "success") and tool_name == "write_file":
            self._edit_count += 1

    async def _approval_callback(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        """Approval callback -> request on_tool_request, waits for Go response."""
        # Check session-level auto-approve
        if tool_name in self._session_approved_tools:
            self._on_tool_call(tool_name, "pending", "(auto-approved)")
            return True

        args_str = json.dumps(arguments, indent=2)
        try:
            result = await self.emit_request("on_tool_request", {
                "tool": tool_name,
                "args": args_str,
            })
        except asyncio.CancelledError:
            return False

        approved = result.get("approved", False)
        session_approve = result.get("session_approve", False)

        if approved and session_approve:
            self._session_approved_tools.add(tool_name)
            if self._approval_manager:
                self._approval_manager.enable_shell()
            return True
        elif approved:
            if tool_name == "run_command" and self._approval_manager:
                self._approval_manager.enable_shell()
            return True
        return False

    async def _ask_user_callback(
        self,
        question: str,
        options: list[str],
        allow_text: bool,
    ) -> str:
        """Ask-user callback -> request on_ask_user, waits for Go response."""
        try:
            result = await self.emit_request("on_ask_user", {
                "question": question,
                "options": options,
                "allow_text": allow_text,
            })
        except asyncio.CancelledError:
            return options[0] if options else ""

        return result.get("answer", "")

    # --- Request handlers ---

    async def handle_chat(self, message: str, session_id: str | None, request_id: int) -> None:
        """Handle a chat request from the Go frontend."""
        if session_id and session_id != self.session_id:
            self.session_id = session_id

        # Auto-title session from first user message
        if not self._session_titled:
            title = message[:60] + ("..." if len(message) > 60 else "")
            self.session_store.update_session(self.session_id, title=title)
            self._session_titled = True

        try:
            agent_loop = self._ensure_agent_loop()
            agent_loop.session_id = self.session_id

            # Always stream thinking tokens to the frontend — the Go TUI
            # decides whether to display them based on its own showThinking flag.
            await agent_loop.run(
                message,
                on_chunk=self._on_chunk,
                on_thinking_chunk=self._on_thinking_chunk,
                on_tool_call=self._on_tool_call,
                approval_callback=self._approval_callback,
                ask_user_callback=self._ask_user_callback,
            )
        except asyncio.CancelledError:
            self.emit_notification("on_done", {
                "tokens_in": 0,
                "tokens_out": 0,
                "cancelled": True,
            })
            return
        except Exception as e:
            logger.exception("Error in handle_chat: %s", e)
            self.emit_notification("on_error", {"message": str(e)})

        self.emit_notification("on_done", {
            "tokens_in": 0,
            "tokens_out": 0,
        })

    async def handle_cancel(self, request_id: int) -> None:
        """Cancel the active agent loop."""
        if self._agent_loop:
            self._agent_loop.cancel()
        if self._agent_task and not self._agent_task.done():
            self._agent_task.cancel()
            try:
                await self._agent_task
            except asyncio.CancelledError:
                pass
        self.emit_response(request_id, {"ok": True})

    async def handle_command(self, cmd: str, request_id: int) -> None:
        """Dispatch a slash command via the CommandRouter."""
        result = self.command_router.dispatch(cmd)
        if result is not None:
            slash_cmd, args = result
            try:
                await slash_cmd.handler(self._app_context, args)
            except EOFError:
                self._running = False
        else:
            self._app_context.add_system_message(f"Unknown command: {cmd}")
        self.emit_response(request_id, {"ok": True})

    async def handle_session_new(self, title: str, request_id: int) -> None:
        """Create a new session."""
        self.session_id = self.session_store.create_session(
            title=title or "New session",
            model=self.config.llm.model,
            provider=self.config.llm.provider,
            project_dir=str(self.project_root),
        )
        self._session_titled = bool(title)
        self._session_approved_tools.clear()
        self._agent_loop = None  # Reset agent loop for new session
        self._emit_status()
        self.emit_response(request_id, {"session_id": self.session_id})

    async def handle_session_list(self, request_id: int) -> None:
        """List all sessions."""
        sessions = self.session_store.list_sessions()
        result = [
            {"id": s.id, "title": s.title, "model": s.model, "provider": s.provider}
            for s in sessions[:20]
        ]
        self.emit_response(request_id, {"sessions": result})

    async def handle_session_resume(self, session_id: str, request_id: int) -> None:
        """Resume a session by ID."""
        sessions = self.session_store.list_sessions()
        match = None
        for s in sessions:
            if s.id.startswith(session_id):
                match = s
                break

        if match is None:
            self.emit_response(request_id, {"error": f"Session not found: {session_id}"})
            return

        self.session_id = match.id
        self._session_titled = True
        self._session_approved_tools.clear()
        self._agent_loop = None
        self._emit_status()
        self.emit_response(request_id, {"session_id": match.id, "title": match.title})

    async def handle_config_get(self, request_id: int) -> None:
        """Return current configuration."""
        self.emit_response(request_id, self.config.model_dump())

    async def handle_config_set(self, key: str, value: str, request_id: int) -> None:
        """Set a configuration value."""
        parts = key.split(".")
        if len(parts) != 2:  # noqa: PLR2004
            self.emit_response(request_id, {"error": "Key must be section.field"})
            return

        section, field = parts
        data = self.config.model_dump()
        if section not in data:
            self.emit_response(request_id, {"error": f"Unknown section: {section}"})
            return
        if field not in data[section]:
            self.emit_response(request_id, {"error": f"Unknown field: {section}.{field}"})
            return

        data[section][field] = value
        self.config = HybridCoderConfig.model_validate(data)
        self._emit_status()
        self.emit_response(request_id, {"ok": True})

    async def handle_shutdown(self, request_id: int) -> None:
        """Gracefully shut down the server."""
        self.emit_response(request_id, {"ok": True})
        self._running = False

    # --- Main loop ---

    async def run(self) -> None:
        """Main event loop: read JSON-RPC messages from stdin and dispatch."""
        self._emit_status()

        loop = asyncio.get_running_loop()
        line_queue: asyncio.Queue[str | None] = asyncio.Queue()

        # Read stdin in a thread to avoid Windows ProactorEventLoop issues
        # with connect_read_pipe (AttributeError: '_empty_waiter').
        import threading

        def _stdin_reader() -> None:
            """Read lines from stdin in a background thread."""
            try:
                for raw_line in sys.stdin:
                    loop.call_soon_threadsafe(line_queue.put_nowait, raw_line)
            except (EOFError, OSError, ValueError):
                pass
            finally:
                loop.call_soon_threadsafe(line_queue.put_nowait, None)

        reader_thread = threading.Thread(target=_stdin_reader, daemon=True)
        reader_thread.start()

        while self._running:
            try:
                line_str_raw = await line_queue.get()
            except Exception:
                break

            if line_str_raw is None:
                break

            line_str = line_str_raw.strip()
            if not line_str:
                continue

            try:
                msg = json.loads(line_str)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON: %s", line_str[:100])
                continue

            # Route message
            msg_id = msg.get("id")
            method = msg.get("method")

            # Response to a request we sent (Python->Go, returned)
            if msg_id is not None and method is None:
                self._route_response(msg_id, msg.get("result", {}))
                continue

            # Request from Go
            if method is None:
                continue

            request_id = msg_id if msg_id is not None else 0
            params = msg.get("params", {})

            try:
                await self._dispatch(method, params, request_id)
            except Exception as e:
                logger.exception("Error dispatching %s: %s", method, e)
                if request_id:
                    self.emit_response(request_id, {"error": str(e)})

    def _route_response(self, request_id: int, result: dict[str, Any]) -> None:
        """Route a response from Go to a pending future."""
        future = self._pending_futures.get(request_id)
        if future and not future.done():
            future.set_result(result)

    async def _dispatch(self, method: str, params: dict[str, Any], request_id: int) -> None:
        """Dispatch a JSON-RPC request to the appropriate handler."""
        if method == "chat":
            message = params.get("message", "")
            session_id = params.get("session_id")
            # Run agent in background task
            self._agent_task = asyncio.create_task(
                self.handle_chat(message, session_id, request_id)
            )
        elif method == "cancel":
            await self.handle_cancel(request_id)
        elif method == "command":
            cmd = params.get("cmd", "")
            await self.handle_command(cmd, request_id)
        elif method == "session.new":
            title = params.get("title", "")
            await self.handle_session_new(title, request_id)
        elif method == "session.list":
            await self.handle_session_list(request_id)
        elif method == "session.resume":
            sid = params.get("session_id", "")
            await self.handle_session_resume(sid, request_id)
        elif method == "config.get":
            await self.handle_config_get(request_id)
        elif method == "config.set":
            key = params.get("key", "")
            value = params.get("value", "")
            await self.handle_config_set(key, value, request_id)
        elif method == "shutdown":
            await self.handle_shutdown(request_id)
        else:
            if request_id:
                self.emit_response(request_id, {"error": f"Unknown method: {method}"})


async def main() -> None:
    """Entry point for the JSON-RPC backend server."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    server = BackendServer()
    await server.run()
