"""Headless NDJSON runner for --json mode.

Implements the ``ChatHost`` protocol subset needed to run a chat turn
and emit Tier 4.4 NDJSON events to stdout.  Reuses
``backend/chat.py::run_chat_turn()`` and
``backend/server.py::BackendServer._ensure_agent_loop()``.

Hard constraints:
  - stdout contains ONLY valid NDJSON (no banners, no log lines)
  - logs/warnings go to stderr
  - does NOT import or spawn the Rust TUI path
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from pathlib import Path
from typing import Any

from autocode.agent.loop import AgentLoop
from autocode.backend import headless_schema as hs
from autocode.backend import schema as rpc_schema
from autocode.config import AutoCodeConfig, load_config
from autocode.core.logging import setup_session_logging
from autocode.session.store import SessionStore

logger = logging.getLogger(__name__)


class _HeadlessTransport:
    def __init__(self, fp: Any) -> None:
        self._fp = fp

    def send_message(self, msg: dict[str, Any]) -> None:
        import json

        line = json.dumps(msg, separators=(",", ":")) + "\n"
        self._fp.write(line)
        self._fp.flush()


class HeadlessRunner:
    """Minimal ChatHost adapter that emits NDJSON events to stdout."""

    def __init__(
        self,
        config: AutoCodeConfig | None = None,
        project_root: Path | None = None,
        *,
        output: Any | None = None,
        auto_approve: bool = False,
    ) -> None:
        self.config = config or load_config()
        self.project_root = project_root or Path.cwd()
        self._output = output or sys.stdout

        db_path = Path(self.config.tui.session_db_path).expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_store = SessionStore(str(db_path))

        self.session_id = self.session_store.create_session(
            title="Headless session",
            model=self.config.llm.model,
            provider=self.config.llm.provider,
            project_dir=str(self.project_root),
        )
        self._session_log_dir = setup_session_logging(
            self.config.logging, self.session_id
        )

        self._session_titled: bool = False
        self._session_stats: Any | None = None
        self._session_approved_tools: set[str] = set()
        self._approval_manager: Any | None = None
        self._context_assembler: Any | None = None
        self._l3_provider: Any | None = None
        self._task_store: Any | None = None
        self._subagent_manager: Any | None = None
        self._edit_count: int = 0
        self._show_thinking: bool = bool(
            getattr(self.config.llm, "reasoning_enabled", True)
        )

        self._provider: Any | None = None
        self._last_provider_selection: Any | None = None
        self._tool_registry: Any | None = None
        self._tool_result_cache: Any | None = None
        self._agent_loop: AgentLoop | None = None
        self._llm_scheduler: Any | None = None
        self._delegation_policy: Any | None = None
        self._memory_store: Any | None = None
        self._checkpoint_store: Any | None = None
        self._agent_mode: Any = None

        self._thread_id: str = uuid.uuid4().hex[:16]
        self._turn_id: str = ""
        self._item_counter: int = 0
        self._auto_approve: bool = auto_approve
        self._current_agent_message_item_id: str | None = None
        self._agent_message_open: bool = False
        self._turn_completed_emitted: bool = False

    def _next_item_id(self) -> str:
        self._item_counter += 1
        return f"item-{self._item_counter}"

    def emit_notification(self, method: str, params: dict[str, Any]) -> None:
        if method == "on_token":
            self._emit_agent_message_delta(params.get("text", ""))
        elif method == "on_thinking_chunk":
            # Reserved for the future `reasoning` item kind; C6.G5 exposes
            # reasoning usage counters but does not stream reasoning content.
            pass
        elif method == "on_tool_call":
            self._emit_tool_call(params)
        elif method == "on_done":
            self._emit_turn_completed(params)
        elif method == "on_error":
            self._emit_error(params.get("message", ""))
        elif method == "on_warning":
            self._emit_stderr_warning(params.get("message", ""))
        elif method == "on_task_state":
            self._emit_plan_update(params)
        elif method == "on_cost_update":
            pass
        elif method == "on_chat_ack":
            pass

    async def emit_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == rpc_schema.METHOD_ON_TOOL_REQUEST:
            approved = bool(getattr(self, "_auto_approve", False))
            self._emit_approval(params, approved=approved)
            return {"approved": approved}
        if method == rpc_schema.METHOD_ON_ASK_USER:
            options = params.get("options", [])
            return {"answer": options[0] if options else ""}
        return {}

    def _emit_cost_update(self) -> None:
        pass

    async def _teardown_agent_resources(self) -> None:
        if self._subagent_manager:
            self._subagent_manager.cancel_all()
            self._subagent_manager = None
        if self._llm_scheduler:
            await self._llm_scheduler.shutdown()
            self._llm_scheduler = None
        self._agent_loop = None
        self._session_stats = None
        self._task_store = None

        from autocode.agent.tools import clear_observed_file_mtimes

        clear_observed_file_mtimes()
        self._memory_store = None
        self._checkpoint_store = None
        self._context_assembler = None

    def _ensure_agent_loop(self) -> AgentLoop:
        if self._agent_loop is None:
            self._provider = __import__(
                "autocode.layer4.llm", fromlist=["create_provider"]
            ).create_provider(self.config)

            from autocode.agent.tool_result_cache import ToolResultCache

            cache_enabled = bool(
                getattr(self.config.agent, "tool_result_cache_enabled", True)
            )
            self._tool_result_cache = ToolResultCache() if cache_enabled else None

            from autocode.agent.approval import ApprovalManager, ApprovalMode
            from autocode.agent.tools import create_default_registry

            self._tool_registry = create_default_registry(
                project_root=str(self.project_root),
                tool_result_cache=self._tool_result_cache,
            )
            self._approval_manager = ApprovalManager(
                mode=ApprovalMode("auto" if self._auto_approve else "suggest"),
                shell_config=self.config.shell,
            )

            from autocode.agent.factory import (
                create_orchestrator,
                load_project_memory_content,
            )
            from autocode.agent.subagent import LLMScheduler, SubagentManager
            from autocode.agent.subagent_tools import register_subagent_tools
            from autocode.agent.task_tools import register_task_tools
            from autocode.core.blob_store import BlobStore
            from autocode.agent.event_recorder import EventRecorder
            from autocode.session.episode_store import EpisodeStore
            from autocode.session.task_store import TaskStore
            from autocode.agent.memory import MemoryStore
            from autocode.session.checkpoint_store import CheckpointStore
            from autocode.agent.delegation import DelegationPolicy

            memory_content = load_project_memory_content(self.project_root)

            self._task_store = TaskStore(
                self.session_store.get_connection(),
                self.session_id,
            )
            register_task_tools(self._tool_registry, self._task_store)

            project_id = str(self.project_root)
            conn = self.session_store.get_connection()
            self._memory_store = MemoryStore(
                conn,
                project_id,
                max_entries=self.config.agent.memory_max_entries,
                max_context_tokens=self.config.agent.memory_context_max_tokens,
            )
            self._memory_store.apply_decay()
            self._checkpoint_store = CheckpointStore(conn, self.session_id)

            try:
                from autocode.layer3.provider import L3Provider

                self._l3_provider = L3Provider(
                    model_path=self.config.layer3.model_path,
                    grammar_constrained=self.config.layer3.grammar_constrained,
                )
            except ImportError:
                logger.warning("L3 dependencies not installed; L3 disabled")
                self._l3_provider = None

            try:
                from autocode.core.context import ContextAssembler

                self._context_assembler = ContextAssembler(
                    context_budget=self.config.layer2.context_budget,
                )
            except ImportError:
                self._context_assembler = None

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
                on_state_change=lambda: None,
                delegation_policy=self._delegation_policy,
            )
            register_subagent_tools(self._tool_registry, self._subagent_manager)

            event_recorder: EventRecorder | None = None
            if self.config.logging.training.enabled:
                blob_dir = (
                    self._session_log_dir / self.config.logging.training.blob_dir
                )
                blob_store = BlobStore(blob_dir)
                episode_store = EpisodeStore(
                    self.session_store.get_connection(),
                    self.session_id,
                    blob_store,
                    max_episodes=self.config.logging.training.max_episodes_per_session,
                )
                event_recorder = EventRecorder(episode_store)

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
                tool_result_cache=self._tool_result_cache,
                cost_limit_usd=self.config.agent.cost_limit_usd,
                checkpoint_store=self._checkpoint_store,
                project_root=self.project_root,
                verify_config=self.config.agent.verify,
            )

        return self._agent_loop

    def _expand_file_mentions(self, message: str) -> str:
        return message

    def _select_chat_layer(self, message: str) -> tuple[int, str, bool]:
        self._apply_layer45_selection("headless_default", confidence=1.0)
        return 4, "headless_default", False

    def _apply_layer45_selection(self, task_class: Any, *, confidence: float) -> None:
        routing = getattr(self.config, "routing", None)
        if not getattr(routing, "enabled", False):
            return
        try:
            from autocode.layer4_5.router import Layer45Router

            router = Layer45Router.from_config(self.config)
            selection = router.select(task_class, confidence=confidence)
        except Exception:
            return
        self._last_provider_selection = selection
        self.config.llm.provider = selection.provider
        self.config.llm.model = selection.model

    # --- NDJSON event emitters ---

    def emit_thread_started(self) -> None:
        hs.emit_event(
            hs.ThreadStartedEvent(
                thread_id=self._thread_id,
                session_id=self.session_id,
            ),
            fp=self._output,
        )

    def emit_turn_started(self, message: str) -> None:
        self._turn_id = uuid.uuid4().hex[:16]
        self._item_counter = 0
        self._current_agent_message_item_id = None
        self._agent_message_open = False
        self._turn_completed_emitted = False
        hs.emit_event(
            hs.TurnStartedEvent(
                turn_id=self._turn_id,
                thread_id=self._thread_id,
                message=message,
            ),
            fp=self._output,
        )

    def _emit_agent_message_delta(self, text: str) -> None:
        """Emit assistant text under one stable `agent_message` item."""
        if not self._agent_message_open:
            self._current_agent_message_item_id = self._next_item_id()
            self._agent_message_open = True
            hs.emit_event(
                hs.ItemStartedEvent(
                    item_id=self._current_agent_message_item_id,
                    turn_id=self._turn_id,
                    kind="agent_message",
                ),
                fp=self._output,
            )
        hs.emit_event(
            hs.ItemDeltaEvent(
                item_id=self._current_agent_message_item_id or "",
                delta=text,
            ),
            fp=self._output,
        )

    def _close_agent_message(self) -> None:
        if not self._agent_message_open or not self._current_agent_message_item_id:
            return
        hs.emit_event(
            hs.ItemCompletedEvent(item_id=self._current_agent_message_item_id),
            fp=self._output,
        )
        self._agent_message_open = False
        self._current_agent_message_item_id = None

    def _emit_tool_call(self, params: dict[str, Any]) -> None:
        item_id = self._next_item_id()
        tool_name = params.get("name", "")
        status = params.get("status", "")
        result = params.get("result", "")

        hs.emit_event(
            hs.ItemStartedEvent(
                item_id=item_id,
                turn_id=self._turn_id,
                kind="tool_execution",
            ),
            fp=self._output,
        )
        hs.emit_event(
            hs.ItemCompletedEvent(
                item_id=item_id,
                result=f"{tool_name}: {status} - {str(result)[:500]}",
            ),
            fp=self._output,
        )

    def _emit_approval(self, params: dict[str, Any], *, approved: bool) -> None:
        item_id = self._next_item_id()
        tool_name = params.get("tool_name") or params.get("name") or "tool"
        decision = "approved" if approved else "denied"
        hs.emit_event(
            hs.ItemStartedEvent(
                item_id=item_id,
                turn_id=self._turn_id,
                kind="approval",
            ),
            fp=self._output,
        )
        hs.emit_event(
            hs.ItemCompletedEvent(
                item_id=item_id,
                result=f"{tool_name}: {decision}",
            ),
            fp=self._output,
        )

    def _emit_plan_update(self, params: dict[str, Any]) -> None:
        item_id = self._next_item_id()
        summary = (
            params.get("summary")
            or params.get("message")
            or params.get("status")
            or str(params)
        )
        hs.emit_event(
            hs.ItemStartedEvent(
                item_id=item_id,
                turn_id=self._turn_id,
                kind="plan_update",
            ),
            fp=self._output,
        )
        hs.emit_event(
            hs.ItemDeltaEvent(item_id=item_id, delta=str(summary)),
            fp=self._output,
        )
        hs.emit_event(
            hs.ItemCompletedEvent(item_id=item_id, result=str(summary)[:500]),
            fp=self._output,
        )

    def _emit_turn_completed(self, params: dict[str, Any]) -> None:
        if self._turn_completed_emitted:
            return
        self._close_agent_message()
        usage = hs.build_usage_from_stats(self._session_stats)
        hs.emit_event(
            hs.TurnCompletedEvent(
                turn_id=self._turn_id,
                thread_id=self._thread_id,
                usage=usage,
            ),
            fp=self._output,
        )
        self._turn_completed_emitted = True

    def _emit_error(self, message: str) -> None:
        hs.emit_event(
            hs.ErrorEvent(message=message),
            fp=self._output,
        )

    def _emit_stderr_warning(self, message: str) -> None:
        print(f"[WARNING] {message}", file=sys.stderr)

    # --- Public API ---

    async def run(self, message: str) -> None:
        from autocode.backend.chat import run_chat_turn

        self.emit_thread_started()
        self.emit_turn_started(message)
        try:
            await run_chat_turn(
                self,
                message=message,
                session_id=None,
                request_id=-1,
            )
        except Exception as exc:
            self._emit_error(str(exc))
        finally:
            self._emit_turn_completed({})
