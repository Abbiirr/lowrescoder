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
import time
from pathlib import Path
from typing import Any

from hybridcoder.agent.approval import ApprovalManager, ApprovalMode
from hybridcoder.agent.context import ContextEngine
from hybridcoder.agent.event_recorder import EventRecorder
from hybridcoder.agent.loop import AgentLoop, AgentMode
from hybridcoder.agent.subagent import LLMScheduler, SubagentManager
from hybridcoder.agent.subagent_tools import register_subagent_tools
from hybridcoder.agent.task_tools import register_task_tools
from hybridcoder.agent.tools import ToolRegistry, create_default_registry
from hybridcoder.config import HybridCoderConfig, load_config
from hybridcoder.core.blob_store import BlobStore
from hybridcoder.core.logging import log_event, setup_session_logging
from hybridcoder.layer4.llm import create_provider
from hybridcoder.session.episode_store import EpisodeStore
from hybridcoder.session.store import SessionStore
from hybridcoder.session.task_store import TaskStore
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

    def set_plan_mode(self, enabled: bool) -> None:
        """Set plan mode. Persists across agent loop recreation."""
        self._server._plan_mode_enabled = enabled
        if self._server._agent_loop:
            mode = AgentMode.PLANNING if enabled else AgentMode.NORMAL
            self._server._agent_loop.set_mode(mode)

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
        self._session_log_dir = setup_session_logging(self.config.logging, self.session_id)

        # Commands
        self.command_router: CommandRouter = create_default_router()
        self._app_context = _ServerAppContext(self)

        # Agent (lazy init)
        self._provider: Any = None
        self._tool_registry: ToolRegistry | None = None
        self._approval_manager: ApprovalManager | None = None
        self._agent_loop: AgentLoop | None = None
        self._agent_task: asyncio.Task[None] | None = None
        self._task_store: TaskStore | None = None
        self._llm_scheduler: LLMScheduler | None = None
        self._subagent_manager: SubagentManager | None = None
        self._session_titled: bool = False

        # Plan mode (persisted across loop recreation)
        self._plan_mode_enabled: bool = False

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

            # Create TaskStore and register task tools
            self._task_store = TaskStore(
                self.session_store.get_connection(), self.session_id,
            )
            register_task_tools(self._tool_registry, self._task_store)

            # Create LLM Scheduler and SubagentManager
            self._llm_scheduler = LLMScheduler()
            self._llm_scheduler.start()
            self._subagent_manager = SubagentManager(
                provider=self._provider,
                tool_registry=self._tool_registry,
                scheduler=self._llm_scheduler,
                max_concurrent=self.config.agent.max_subagents,
                max_iterations=self.config.agent.subagent_max_iterations,
                timeout_seconds=self.config.agent.subagent_timeout_seconds,
            )
            register_subagent_tools(self._tool_registry, self._subagent_manager)

            # Create ContextEngine
            context_engine = ContextEngine(
                provider=self._provider,
                session_store=self.session_store,
                context_length=self.config.llm.context_length,
                compaction_threshold=self.config.agent.compaction_threshold,
            )

            # Training-grade event recorder (opt-in)
            event_recorder: EventRecorder | None = None
            if self.config.logging.training.enabled:
                blob_dir = self._session_log_dir / self.config.logging.training.blob_dir
                blob_store = BlobStore(blob_dir)
                episode_store = EpisodeStore(
                    self.session_store.get_connection(),
                    self.session_id,
                    blob_store,
                    max_episodes=self.config.logging.training.max_episodes_per_session,
                )
                event_recorder = EventRecorder(episode_store)

            self._agent_loop = AgentLoop(
                provider=self._provider,
                tool_registry=self._tool_registry,
                approval_manager=self._approval_manager,
                session_store=self.session_store,
                session_id=self.session_id,
                memory_content=memory_content,
                context_engine=context_engine,
                task_store=self._task_store,
                event_recorder=event_recorder,
                subagent_manager=self._subagent_manager,
            )

            # Apply persisted plan mode
            if self._plan_mode_enabled:
                self._agent_loop.set_mode(AgentMode.PLANNING)

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
            if tool_name == "run_command" and self._approval_manager:
                self._approval_manager.enable_shell()
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

        if approved and tool_name == "run_command" and self._approval_manager:
            self._approval_manager.enable_shell()

        return approved  # type: ignore[no-any-return]

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

        return result.get("answer", "")  # type: ignore[no-any-return]

    # --- Lifecycle helpers ---

    async def _teardown_agent_resources(self) -> None:
        """Cleanly tear down subagent manager, scheduler, and agent loop.

        Called on session transitions and shutdown to prevent orphan tasks.
        """
        if self._subagent_manager:
            self._subagent_manager.cancel_all()
            self._subagent_manager = None
        if self._llm_scheduler:
            await self._llm_scheduler.shutdown()
            self._llm_scheduler = None
        self._agent_loop = None
        self._task_store = None

    # --- Request handlers ---

    async def handle_chat(self, message: str, session_id: str | None, request_id: int) -> None:
        """Handle a chat request from the Go frontend."""
        if session_id and session_id != self.session_id:
            self.session_id = session_id
            self._session_log_dir = setup_session_logging(
                self.config.logging, self.session_id,
            )
            await self._teardown_agent_resources()
            self._session_approved_tools.clear()

        # Auto-title session from first user message
        if not self._session_titled:
            title = message[:60] + ("..." if len(message) > 60 else "")
            self.session_store.update_session(self.session_id, title=title)
            self._session_titled = True

        # --- Layer routing (Phase 3) ---
        layer_used = 4  # Default to L4

        try:
            from hybridcoder.core.router import RequestRouter
            from hybridcoder.core.types import RequestType

            router = RequestRouter(self.config.layer1)

            if self.config.layer1.enabled:
                request_type = router.classify(message)

                # L1 bypass: deterministic queries (zero tokens, <50ms)
                if request_type == RequestType.DETERMINISTIC_QUERY:
                    try:
                        from hybridcoder.layer1.queries import DeterministicQueryHandler

                        handler = DeterministicQueryHandler(
                            project_root=self.project_root,
                        )
                        response = handler.handle(message)
                        self.emit_notification("on_token", {"text": response.content})
                        self.emit_notification("on_done", {
                            "tokens_in": 0,
                            "tokens_out": 0,
                            "layer_used": 1,
                        })
                        return
                    except ImportError:
                        pass  # tree-sitter not available, fall through to L4
        except ImportError:
            pass  # Router not available, use L4

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
                "layer_used": layer_used,
            })
            return
        except Exception as e:
            logger.exception("Error in handle_chat: %s", e)
            self.emit_notification("on_error", {"message": str(e)})

        self.emit_notification("on_done", {
            "tokens_in": 0,
            "tokens_out": 0,
            "layer_used": layer_used,
        })

    async def handle_cancel(self, request_id: int) -> None:
        """Cancel the active agent loop and propagate to subagents."""
        if self._agent_loop:
            self._agent_loop.cancel()
        if self._subagent_manager:
            self._subagent_manager.cancel_all()
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
        self._session_log_dir = setup_session_logging(self.config.logging, self.session_id)
        self._session_titled = bool(title)
        self._session_approved_tools.clear()
        await self._teardown_agent_resources()
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
        session_id = session_id.strip()
        if not session_id:
            msg = "Session ID is required"
            self.emit_notification("on_error", {"message": msg})
            self.emit_response(request_id, {"error": msg})
            return

        sessions = self.session_store.list_sessions()
        matches = [s for s in sessions if s.id.startswith(session_id)]

        if not matches:
            msg = f"Session not found: {session_id}"
            self.emit_notification("on_error", {"message": msg})
            self.emit_response(request_id, {"error": msg})
            return

        if len(matches) > 1:
            sample = ", ".join(s.id[:8] for s in matches[:5])
            msg = f"Ambiguous session prefix '{session_id}'. Matches: {sample}"
            self.emit_notification("on_error", {"message": msg})
            self.emit_response(
                request_id,
                {"error": msg},
            )
            return

        match = matches[0]
        self.session_id = match.id
        self._session_log_dir = setup_session_logging(self.config.logging, self.session_id)
        self._session_titled = True
        self._session_approved_tools.clear()
        await self._teardown_agent_resources()
        self._emit_status()
        self.emit_response(request_id, {"session_id": match.id, "title": match.title})

    async def handle_task_list(self, request_id: int) -> None:
        """List tasks for the current session."""
        if self._task_store is None:
            self._task_store = TaskStore(
                self.session_store.get_connection(), self.session_id,
            )
        tasks = self._task_store.list_tasks()
        self.emit_response(request_id, {
            "tasks": [t.model_dump(mode="json") for t in tasks],
        })

    async def handle_subagent_list(self, request_id: int) -> None:
        """List all subagents (active and completed)."""
        if self._subagent_manager is None:
            self.emit_response(request_id, {"subagents": []})
            return
        self.emit_response(request_id, {
            "subagents": self._subagent_manager.list_all(),
        })

    async def handle_subagent_cancel(self, subagent_id: str, request_id: int) -> None:
        """Cancel a running subagent."""
        if self._subagent_manager is None:
            self.emit_response(request_id, {"success": False})
            return
        success = self._subagent_manager.cancel(subagent_id)
        self.emit_response(request_id, {"success": success})

    async def handle_plan_status(self, request_id: int) -> None:
        """Return current plan mode status (from persisted server state)."""
        if self._agent_loop:
            mode = self._agent_loop.get_mode().value
        else:
            mode = AgentMode.PLANNING.value if self._plan_mode_enabled else AgentMode.NORMAL.value
        self.emit_response(request_id, {"mode": mode})

    async def handle_plan_set(self, mode: str, request_id: int) -> None:
        """Set plan mode (persisted on server, applied to loop if exists)."""
        try:
            agent_mode = AgentMode(mode)
        except ValueError:
            self.emit_response(request_id, {
                "error": f"Invalid mode '{mode}'. Use 'normal' or 'planning'.",
            })
            return
        old_enabled = self._plan_mode_enabled
        self._plan_mode_enabled = agent_mode == AgentMode.PLANNING
        if self._agent_loop:
            self._agent_loop.set_mode(agent_mode)
        self.emit_response(request_id, {
            "mode": agent_mode.value,
            "changed": old_enabled != self._plan_mode_enabled,
        })

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
        await self._teardown_agent_resources()
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
                log_event(logger, logging.WARNING, "rpc_error", error="invalid_json")
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
        _dispatch_start = time.monotonic()
        log_event(logger, logging.DEBUG, "rpc_request", method=method, request_id=request_id)
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
        elif method == "task.list":
            await self.handle_task_list(request_id)
        elif method == "subagent.list":
            await self.handle_subagent_list(request_id)
        elif method == "subagent.cancel":
            sid = params.get("subagent_id", "")
            await self.handle_subagent_cancel(sid, request_id)
        elif method == "plan.status":
            await self.handle_plan_status(request_id)
        elif method == "plan.set":
            mode = params.get("mode", "normal")
            await self.handle_plan_set(mode, request_id)
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
        log_event(
            logger, logging.DEBUG, "rpc_response",
            method=method, request_id=request_id,
            duration_ms=int((time.monotonic() - _dispatch_start) * 1000),
        )


async def main() -> None:
    """Entry point for the JSON-RPC backend server."""
    from hybridcoder.core.logging import setup_logging

    config = load_config()
    setup_logging(config.logging)
    server = BackendServer(config=config)
    await server.run()
