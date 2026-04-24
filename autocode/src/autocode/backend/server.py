"""JSON-RPC backend server for the Rust TUI and compatible frontend clients.

Communicates via newline-delimited JSON-RPC 2.0 over stdin/stdout.
Mirrors the InlineApp agent loop but exposes it via RPC instead of a
prompt_toolkit UI.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import sys
import time
from collections.abc import Coroutine
from pathlib import Path
from typing import Any

from autocode.agent.approval import ApprovalManager, ApprovalMode
from autocode.agent.delegation import DelegationPolicy
from autocode.agent.event_recorder import EventRecorder
from autocode.agent.loop import AgentLoop, AgentMode
from autocode.agent.memory import MemoryStore
from autocode.agent.subagent import LLMScheduler, SubagentManager
from autocode.agent.subagent_tools import register_subagent_tools
from autocode.agent.task_tools import register_task_tools
from autocode.agent.tools import ToolRegistry, create_default_registry
from autocode.app.commands import CommandRouter, create_default_router
from autocode.backend import chat as backend_chat
from autocode.backend import schema as rpc_schema
from autocode.backend import services as backend_services
from autocode.backend.dispatcher import dispatch_request
from autocode.backend.stdio_host import StdioJsonRpcHost
from autocode.backend.tcp_host import TcpJsonRpcHost
from autocode.backend.transport import BackendTransport, PendingRequestBroker, StdoutTransport
from autocode.config import AutoCodeConfig, load_config
from autocode.core.blob_store import BlobStore
from autocode.core.logging import log_event, setup_session_logging
from autocode.layer4.llm import create_provider
from autocode.session.checkpoint_store import CheckpointStore
from autocode.session.episode_store import EpisodeStore
from autocode.session.store import SessionStore
from autocode.session.task_store import TaskStore

logger = logging.getLogger(__name__)

# Python->Go request IDs start at 1000 to avoid collision with Go->Python IDs.
_PYTHON_REQUEST_ID_START = 1000


class _ServerAppContext:
    """Minimal adapter implementing the AppContext protocol for slash commands.

    Routes UI operations to JSON-RPC notifications so the frontend can
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
    def config(self) -> AutoCodeConfig:
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
        from autocode.app.commands import _copy_to_clipboard

        return _copy_to_clipboard(text)

    def set_plan_mode(self, enabled: bool) -> None:
        """Set plan mode. Persists across agent loop recreation."""
        mode = AgentMode.PLANNING if enabled else AgentMode.NORMAL
        self.set_agent_mode(mode)

    def set_agent_mode(self, mode: AgentMode) -> None:
        """Set agent mode. Persists across agent loop recreation."""
        self._server._agent_mode = mode
        self._server._plan_mode_enabled = mode == AgentMode.PLANNING
        if self._server._agent_loop:
            self._server._agent_loop.set_mode(mode)

    def exit_app(self) -> None:
        self._server._running = False

    async def run_loop_prompt(self, payload: str) -> None:
        """Execute loop prompt payload through backend chat pipeline."""
        await self._server.handle_chat(payload, None, request_id=-1)

    async def run_loop_command(self, payload: str) -> None:
        """Execute loop slash payload through backend command router."""
        result = self._server.command_router.dispatch(payload)
        if result is None:
            self.add_system_message(f"Unknown command: {payload}")
            return
        slash_cmd, args = result
        await slash_cmd.handler(self, args)


class BackendServer:
    """JSON-RPC server that manages the agent loop and communicates with the frontend."""

    def __init__(
        self,
        config: AutoCodeConfig | None = None,
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
        self._delegation_policy: DelegationPolicy | None = None
        self._memory_store: MemoryStore | None = None
        self._checkpoint_store: CheckpointStore | None = None
        self._l3_provider: Any = None
        self._context_assembler: Any = None
        self._session_titled: bool = False

        # Agent mode (persisted across loop recreation)
        self._agent_mode: AgentMode = AgentMode.NORMAL
        self._plan_mode_enabled: bool = False

        # Thinking visibility
        self._show_thinking: bool = False

        # Session-level auto-approve tracking
        self._session_approved_tools: set[str] = set()

        # Stats
        self._total_tokens_in: int = 0
        self._total_tokens_out: int = 0
        self._edit_count: int = 0
        self._session_stats: Any | None = None

        # Wire protocol state
        self._request_broker = PendingRequestBroker(next_request_id=_PYTHON_REQUEST_ID_START)
        self._running: bool = True
        self._transport: BackendTransport | None = StdoutTransport()

    @property
    def _next_request_id(self) -> int:
        return self._request_broker.next_request_id

    @_next_request_id.setter
    def _next_request_id(self, value: int) -> None:
        self._request_broker.next_request_id = value

    @property
    def _pending_futures(self) -> dict[int, asyncio.Future[dict[str, Any]]]:
        return self._request_broker.pending_futures

    def set_transport(self, transport: BackendTransport | None) -> None:
        """Attach or detach the active frontend transport."""
        if transport is None and self._transport is not None:
            self._request_broker.cancel_all("backend transport detached")
        self._transport = transport

    # --- Wire protocol ---

    def _expand_file_mentions(self, message: str) -> str:
        """Extract @path references and inline file contents."""
        import re

        pattern = re.compile(r"@([\w./\-]+\.\w+)")
        mentions = pattern.findall(message)
        if not mentions:
            return message
        context_parts = []
        for rel_path in mentions:
            abs_path = self.project_root / rel_path
            if abs_path.is_file():
                try:
                    content = abs_path.read_text(encoding="utf-8", errors="replace")
                    if len(content) > 10000:
                        content = content[:10000] + "\n...(truncated)"
                    context_parts.append(f"[File: {rel_path}]\n{content}\n[/File]")
                except Exception:
                    context_parts.append(f"[File: {rel_path}] (could not read)\n[/File]")
        if context_parts:
            clean_msg = pattern.sub(r"`\1`", message)
            return clean_msg + "\n\n" + "\n\n".join(context_parts)
        return message

    def emit_notification(self, method: str, params: dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no ID) to the frontend."""
        msg = {"jsonrpc": "2.0", "method": method, "params": params}
        self._write_message(msg)

    def emit_response(self, request_id: int, result: Any) -> None:
        """Send a JSON-RPC response to a Go->Python request."""
        msg = {"jsonrpc": "2.0", "id": request_id, "result": result}
        self._write_message(msg)

    async def emit_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC request to the frontend and wait for the response."""
        return await self._request_broker.emit_request(self._transport, method, params)

    def _write_message(self, msg: dict[str, Any]) -> None:
        """Write one JSON-RPC message through the active transport."""
        if self._transport is None:
            raise RuntimeError("No backend transport attached")
        self._transport.send_message(msg)

    def _emit_status(self) -> None:
        """Emit current status to the frontend."""
        mode = self.config.tui.approval_mode
        if self._approval_manager:
            mode = self._approval_manager.mode.value
        self.emit_notification(
            "on_status",
            {
                "model": self.config.llm.model,
                "provider": self.config.llm.provider,
                "mode": mode,
                "session_id": self.session_id,
            },
        )

    def _emit_cost_update(self) -> None:
        """Emit per-turn cost/token update to the frontend status bar.

        This is a per-turn notification emitted alongside ``on_done``.
        Honest contract: this is *not* live-streaming cost — it is a
        snapshot taken after each agent turn completes.
        """
        tokens_in = 0
        tokens_out = 0
        if self._session_stats:
            tokens = self._session_stats.token_tracker.total
            tokens_in = tokens.prompt_tokens
            tokens_out = tokens.completion_tokens
        self._total_tokens_in += tokens_in
        self._total_tokens_out += tokens_out
        self.emit_notification(
            "on_cost_update",
            {
                "cost": "0.0000",
                "tokens_in": self._total_tokens_in,
                "tokens_out": self._total_tokens_out,
            },
        )

    @staticmethod
    def _env_flag_enabled(name: str) -> bool:
        value = os.environ.get(name, "").strip().lower()
        return value in {"1", "true", "yes", "on"}

    def _force_l4_routing(self) -> bool:
        return self._env_flag_enabled("AUTOCODE_FORCE_L4")

    def _select_chat_layer(self, message: str) -> tuple[int, str, bool]:
        if self._force_l4_routing():
            return 4, "forced_l4", True

        try:
            from autocode.core.router import RequestRouter
            from autocode.core.types import RequestType
        except ImportError:
            return 4, "router_unavailable", False

        router = RequestRouter(self.config.layer1)
        request_type = router.classify(message)

        if self.config.layer1.enabled and request_type == RequestType.DETERMINISTIC_QUERY:
            return 1, request_type.value, False

        if self.config.layer2.enabled and self._context_assembler:
            if request_type == RequestType.SEMANTIC_SEARCH:
                return 2, request_type.value, False

        if self.config.layer3.enabled and self._l3_provider:
            if request_type == RequestType.SIMPLE_EDIT:
                return 3, request_type.value, False

        return 4, request_type.value, False

    def _emit_chat_ack(self, request_id: int) -> None:
        self.emit_notification(
            rpc_schema.METHOD_ON_CHAT_ACK,
            {
                "request_id": request_id,
                "session_id": self.session_id,
            },
        )

    # --- Agent loop setup (mirrors InlineApp._ensure_agent_loop) ---

    def _ensure_agent_loop(self) -> AgentLoop:
        """Lazy-initialize agent loop with all dependencies."""
        if self._agent_loop is None:
            self._provider = create_provider(self.config)
            from autocode.agent.tool_result_cache import ToolResultCache

            self._tool_result_cache = ToolResultCache()
            self._tool_registry = create_default_registry(
                project_root=str(self.project_root),
                tool_result_cache=self._tool_result_cache,
            )
            self._approval_manager = ApprovalManager(
                mode=ApprovalMode(self.config.tui.approval_mode),
                shell_config=self.config.shell,
            )

            from autocode.agent.factory import (
                create_orchestrator,
                load_project_memory_content,
            )

            # Load project memory + always-on rules (CLAUDE.md, AGENTS.md, .rules/*.md)
            memory_content = load_project_memory_content(self.project_root)

            # Create TaskStore and register task tools
            self._task_store = TaskStore(
                self.session_store.get_connection(),
                self.session_id,
            )
            register_task_tools(self._tool_registry, self._task_store)

            # Sprint 4C: MemoryStore + CheckpointStore
            project_id = str(self.project_root)
            conn = self.session_store.get_connection()
            self._memory_store = MemoryStore(
                conn,
                project_id,
                max_entries=self.config.agent.memory_max_entries,
                max_context_tokens=self.config.agent.memory_context_max_tokens,
            )
            self._memory_store.apply_decay()  # decay at session start
            self._checkpoint_store = CheckpointStore(conn, self.session_id)

            # Sprint 4C: L3Provider (graceful degradation)
            try:
                from autocode.layer3.provider import L3Provider

                self._l3_provider = L3Provider(
                    model_path=self.config.layer3.model_path,
                    grammar_constrained=self.config.layer3.grammar_constrained,
                )
            except ImportError:
                logger.warning("L3 dependencies not installed; L3 disabled")
                self._l3_provider = None

            # Sprint 4C: ContextAssembler
            try:
                from autocode.core.context import ContextAssembler

                self._context_assembler = ContextAssembler(
                    context_budget=self.config.layer2.context_budget,
                )
            except ImportError:
                self._context_assembler = None

            # Create LLM Scheduler and SubagentManager
            self._llm_scheduler = LLMScheduler()
            self._llm_scheduler.start()
            self._delegation_policy = DelegationPolicy(
                max_threads=self.config.agent.max_subagents,
            )
            self._subagent_manager = SubagentManager(
                provider=self._provider,
                tool_registry=self._tool_registry,
                scheduler=self._llm_scheduler,
                max_concurrent=self.config.agent.max_subagents,
                max_iterations=self.config.agent.subagent_max_iterations,
                timeout_seconds=self.config.agent.subagent_timeout_seconds,
                on_state_change=self._emit_task_state,
                delegation_policy=self._delegation_policy,
            )
            register_subagent_tools(self._tool_registry, self._subagent_manager)

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

            # Sprint 4C: inject learned memory context
            memory_context = ""
            if self._memory_store:
                memory_context = self._memory_store.get_context()

            self._agent_loop, self._session_stats = create_orchestrator(
                provider=self._provider,
                tool_registry=self._tool_registry,
                approval_manager=self._approval_manager,
                session_store=self.session_store,
                session_id=self.session_id,
                memory_content=memory_content,
                task_store=self._task_store,
                event_recorder=event_recorder,
                subagent_manager=self._subagent_manager,
                memory_context=memory_context,
                delegation_policy=self._delegation_policy,
                context_length=self.config.llm.context_length,
                compaction_threshold=self.config.agent.compaction_threshold,
                layer2_config=self.config.layer2,
            )

            # Apply persisted agent mode
            if self._agent_mode != AgentMode.NORMAL:
                self._agent_loop.set_mode(self._agent_mode)

        return self._agent_loop

    # --- Agent loop callbacks (map to JSON-RPC) ---

    def _on_chunk(self, text: str) -> None:
        """Stream token callback -> notification on_token."""
        backend_chat.on_chunk(self, text)

    def _on_thinking_chunk(self, text: str) -> None:
        """Thinking token callback -> notification on_thinking."""
        backend_chat.on_thinking_chunk(self, text)

    def _on_tool_call(self, tool_name: str, status: str, result: str = "") -> None:
        """Tool call status callback -> notification on_tool_call."""
        backend_chat.on_tool_call(self, tool_name, status, result)

    def _emit_task_state(self) -> None:
        """Emit on_task_state notification with tasks and subagents."""
        backend_chat.emit_task_state(self)

    async def _approval_callback(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        """Approval callback -> request on_tool_request, waits for Go response."""
        return await backend_chat.approval_callback(self, tool_name, arguments)

    async def _ask_user_callback(
        self,
        question: str,
        options: list[str],
        allow_text: bool,
    ) -> str:
        """Ask-user callback -> request on_ask_user, waits for Go response."""
        return await backend_chat.ask_user_callback(self, question, options, allow_text)

    # --- Lifecycle helpers ---

    async def _teardown_agent_resources(self) -> None:
        """Cleanly tear down subagent manager, scheduler, and agent loop.

        Called on session transitions and shutdown to prevent orphan tasks.
        """
        current_task = asyncio.current_task()

        if self._agent_task and self._agent_task is not current_task:
            if not self._agent_task.done():
                if self._agent_loop:
                    self._agent_loop.cancel()
                self._agent_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._agent_task
            self._agent_task = None

        # Learn from session before teardown
        if self._memory_store and self.session_store and self.session_id:
            try:
                await self._memory_store.learn_from_session(
                    self.session_id,
                    self.session_store,
                    self._provider,
                    self._llm_scheduler,
                )
            except Exception:
                logger.warning("Failed to learn from session", exc_info=True)

        if self._subagent_manager:
            self._subagent_manager.cancel_all()
            self._subagent_manager = None
        if self._llm_scheduler:
            await self._llm_scheduler.shutdown()
            self._llm_scheduler = None
        if self._l3_provider and hasattr(self._l3_provider, "cleanup"):
            self._l3_provider.cleanup()
            self._l3_provider = None
        self._agent_loop = None
        self._session_stats = None
        self._task_store = None

        from autocode.agent.tools import clear_observed_file_mtimes

        clear_observed_file_mtimes()
        self._memory_store = None
        self._checkpoint_store = None
        self._context_assembler = None

    def _apply_session_transition(self, transition: backend_services.SessionTransition) -> None:
        """Apply the host-visible state from a session transition."""
        self.session_id = transition.session_id
        self._session_log_dir = transition.session_log_dir
        self._session_titled = transition.session_titled
        self._session_approved_tools.clear()

    # --- Request handlers ---

    async def handle_chat(self, message: str, session_id: str | None, request_id: int) -> None:
        """Handle a chat request from the frontend."""
        await backend_chat.run_chat_turn(
            self,
            message=message,
            session_id=session_id,
            request_id=request_id,
        )

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
        """Dispatch a slash command via the CommandRouter.

        After any slash command that can mutate model/provider/mode state,
        emit a fresh status notification so the frontend footer reflects the
        new value immediately (fixes Codex Entry 1071 blocker #1: visible
        current-model state was stale after switching).
        """
        try:
            result = await backend_services.execute_command(
                cmd=cmd,
                command_router=self.command_router,
                app_context=self._app_context,
                config=self.config,
            )
        except EOFError:
            self._running = False
            self.emit_response(request_id, {"ok": True})
            return

        if result.status_changed:
            self._emit_status()

        self.emit_response(request_id, result.payload)

    async def handle_command_list(self, request_id: int) -> None:
        """List backend-owned slash commands for Stage 2 surfaces."""
        self.emit_response(
            request_id,
            backend_services.build_command_list_payload(self.command_router),
        )

    async def handle_session_new(self, title: str, request_id: int) -> None:
        """Create a new session."""
        transition = await backend_services.create_session_transition(
            title=title,
            config=self.config,
            project_root=self.project_root,
            session_store=self.session_store,
            teardown_agent_resources=self._teardown_agent_resources,
        )
        self._apply_session_transition(transition)
        self._emit_status()
        self.emit_response(
            request_id,
            {"session_id": transition.session_id, "title": transition.title},
        )

    async def handle_session_list(self, request_id: int) -> None:
        """List all sessions."""
        self.emit_response(
            request_id,
            backend_services.build_session_list_payload(self.session_store),
        )

    async def handle_provider_list(self, request_id: int) -> None:
        """List supported LLM providers (for the frontend picker).

        Returns the same ``_SUPPORTED_PROVIDERS`` tuple the ``/provider``
        handler validates against, so the picker always agrees with the
        text-input path.
        """
        self.emit_response(request_id, backend_services.build_provider_list_payload(self.config))

    async def handle_model_list(self, request_id: int) -> None:
        """List available models for the current provider (for the frontend picker)."""
        try:
            payload = backend_services.build_model_list_payload(self.config)
        except backend_services.BackendServiceError as exc:
            self.emit_response(request_id, {"error": str(exc)})
            return
        self.emit_response(request_id, payload)

    async def handle_session_resume(self, session_id: str, request_id: int) -> None:
        """Resume a session by ID."""
        try:
            transition = await backend_services.resume_session_transition(
                session_id=session_id,
                config=self.config,
                session_store=self.session_store,
                teardown_agent_resources=self._teardown_agent_resources,
            )
        except backend_services.BackendServiceError as exc:
            msg = str(exc)
            self.emit_notification("on_error", {"message": msg})
            self.emit_response(request_id, {"error": msg})
            return

        self._apply_session_transition(transition)
        self._emit_status()
        self.emit_response(
            request_id,
            {"session_id": transition.session_id, "title": transition.title},
        )

    async def handle_task_list(self, request_id: int) -> None:
        """List tasks for the current session."""
        self._task_store = backend_services.ensure_task_store(
            self._task_store,
            session_store=self.session_store,
            session_id=self.session_id,
        )
        self.emit_response(request_id, backend_services.build_task_list_payload(self._task_store))

    async def handle_subagent_list(self, request_id: int) -> None:
        """List all subagents (active and completed)."""
        self.emit_response(
            request_id,
            backend_services.build_subagent_list_payload(self._subagent_manager),
        )

    async def handle_subagent_cancel(self, subagent_id: str, request_id: int) -> None:
        """Cancel a running subagent."""
        self.emit_response(
            request_id,
            backend_services.cancel_subagent(self._subagent_manager, subagent_id),
        )

    async def handle_plan_status(self, request_id: int) -> None:
        """Return current plan mode status (from persisted server state)."""
        self.emit_response(
            request_id,
            backend_services.build_plan_status_payload(self._agent_loop, self._agent_mode),
        )

    async def handle_plan_set(self, mode: str, request_id: int) -> None:
        """Set plan mode (persisted on server, applied to loop if exists)."""
        try:
            update = backend_services.update_plan_mode(
                mode=mode,
                current_mode=self._agent_mode,
                agent_loop=self._agent_loop,
            )
        except backend_services.BackendServiceError as exc:
            self.emit_response(request_id, {"error": str(exc)})
            return

        self._agent_mode = update.agent_mode
        self._plan_mode_enabled = update.plan_mode_enabled
        self.emit_response(
            request_id,
            {
                "mode": update.agent_mode.value,
                "changed": update.changed,
            },
        )

    async def handle_config_get(self, request_id: int) -> None:
        """Return current configuration."""
        self.emit_response(request_id, backend_services.build_config_payload(self.config))

    async def handle_config_set(self, key: str, value: str, request_id: int) -> None:
        """Set a configuration value."""
        try:
            update = backend_services.update_config(
                config=self.config,
                key=key,
                value=value,
            )
        except backend_services.BackendServiceError as exc:
            self.emit_response(request_id, {"error": str(exc)})
            return

        self.config = update.config
        self._emit_status()
        self.emit_response(request_id, {"ok": True})

    async def handle_memory_list(self, request_id: int) -> None:
        """List learned memories for the current project."""
        self.emit_response(
            request_id,
            backend_services.build_memory_list_payload(self._memory_store),
        )

    async def handle_checkpoint_list(self, request_id: int) -> None:
        """List checkpoints for the current session."""
        self.emit_response(
            request_id,
            backend_services.build_checkpoint_list_payload(self._checkpoint_store),
        )

    async def handle_checkpoint_restore(self, checkpoint_id: str, request_id: int) -> None:
        """Restore a checkpoint for the current session."""
        try:
            payload = backend_services.restore_checkpoint(
                checkpoint_store=self._checkpoint_store,
                task_store=self._task_store,
                session_store=self.session_store,
                checkpoint_id=checkpoint_id,
            )
        except backend_services.BackendServiceError as exc:
            self.emit_response(request_id, {"error": str(exc)})
            return
        self.emit_response(request_id, payload)

    async def handle_plan_export(self, request_id: int) -> None:
        """Export task state as a markdown plan artifact."""
        try:
            payload = backend_services.export_plan_artifact(
                session_id=self.session_id,
                task_store=self._task_store,
                subagent_manager=self._subagent_manager,
                project_root=self.project_root,
            )
        except backend_services.BackendServiceError as exc:
            self.emit_response(request_id, {"error": str(exc)})
            return
        self.emit_response(request_id, payload)

    async def handle_plan_sync(self, path: str, request_id: int) -> None:
        """Sync task state from a markdown plan artifact."""
        try:
            payload = backend_services.sync_plan_artifact(
                session_id=self.session_id,
                task_store=self._task_store,
                path=path,
            )
        except backend_services.BackendServiceError as exc:
            self.emit_response(request_id, {"error": str(exc)})
            return
        self.emit_response(request_id, payload)

    async def handle_steer(self, message: str, request_id: int) -> None:
        """Inject a steer message into the active agent run.

        If a run is active, cancel it and persist the steer message as a
        user message in the current session. The frontend receives the
        ``on_done`` notification from the cancelled run and can present
        the steer result immediately.

        If no run is active, returns a structured error so the caller can
        distinguish "nothing to steer" from a real failure.
        """
        self.emit_response(
            request_id,
            backend_services.inject_steer(
                message=message,
                agent_task=self._agent_task,
                agent_loop=self._agent_loop,
                session_store=self.session_store,
                session_id=self.session_id,
            ),
        )

    async def handle_session_fork(self, request_id: int) -> None:
        """Fork the current session into a new one.

        Creates a new session with the same messages as the current
        session.  The backend does *not* switch to the new session — the
        The frontend controls session switching via ``session.resume``.
        """
        payload = backend_services.fork_session(
            session_store=self.session_store,
            source_session_id=self.session_id,
            config=self.config,
            project_root=self.project_root,
        )
        self._emit_status()
        self.emit_response(request_id, payload)

    async def handle_shutdown(self, request_id: int) -> None:
        """Gracefully shut down the server."""
        await self._teardown_agent_resources()
        self.emit_response(request_id, {"ok": True})
        self._running = False

    # --- Main loop ---

    async def run(self) -> None:
        """Main event loop for the default stdio host."""
        await StdioJsonRpcHost(self, stdin=sys.stdin, stdout=sys.stdout).run()

    def _route_response(self, request_id: int, result: dict[str, Any]) -> None:
        """Route a response from Go to a pending future."""
        self._request_broker.route_response(request_id, result)

    def _loop_create_task(self, coroutine: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
        """Create a task on the current event loop.

        Exposed as a small host hook so dispatch ownership can live outside
        ``BackendServer`` without reaching for global asyncio helpers directly.
        """
        return asyncio.create_task(coroutine)

    async def _dispatch(self, method: str, params: dict[str, Any], request_id: int) -> None:
        """Dispatch a JSON-RPC request to the appropriate handler."""
        _dispatch_start = time.monotonic()
        log_event(logger, logging.DEBUG, "rpc_request", method=method, request_id=request_id)
        await dispatch_request(self, method, params, request_id)
        log_event(
            logger,
            logging.DEBUG,
            "rpc_response",
            method=method,
            request_id=request_id,
            duration_ms=int((time.monotonic() - _dispatch_start) * 1000),
        )


async def main(
    *,
    transport: str = "stdio",
    bind_host: str = "127.0.0.1",
    port: int = 8765,
) -> None:
    """Entry point for the JSON-RPC backend server."""
    from autocode.core.logging import setup_logging

    config = load_config()
    setup_logging(config.logging)
    server = BackendServer(config=config)
    if transport == "tcp":
        await TcpJsonRpcHost(server, bind_host=bind_host, port=port).run()
        return
    await server.run()
