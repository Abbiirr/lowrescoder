"""Agent loop: LLM <-> tool execution cycle."""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import logging
import subprocess
import threading
import time
from collections.abc import Awaitable, Callable
from enum import Enum
from pathlib import Path
from typing import Any

from autocode.agent.approval import ApprovalManager, ApprovalMode
from autocode.agent.auto_verify import AutoVerifyConfig, verify_after_edit
from autocode.agent.context import ContextEngine
from autocode.agent.event_recorder import EventRecorder
from autocode.agent.git_aware_staging import stage_post_edit
from autocode.agent.hooks import HookEvent
from autocode.agent.prompt_cache_keepalive import (
    PromptCacheKeepalive,
    PromptCacheKeepaliveConfig,
)
from autocode.agent.prompts import build_dynamic_suffix, build_static_prefix
from autocode.agent.tool_result_cache import ToolResultCache
from autocode.agent.tools import CACHE_MANAGEMENT_TOOL_NAMES, ToolRegistry
from autocode.core.logging import log_debug_prompt, log_event
from autocode.layer1.preview import build_active_symbol_preview
from autocode.layer4.llm import LLMResponse, ToolCall
from autocode.session.store import SessionStore
from autocode.session.task_store import TaskStore

logger = logging.getLogger(__name__)

_TOOL_TERMINATION_PREFIX = "__AUTOCODE_TOOL_TERMINATE__:"
_SYMBOL_PREVIEW_DEADLINE_MS = 100


def encode_tool_termination(display_result: str, final_response: str) -> str:
    """Encode a tool result that should terminate the agent loop."""
    payload = json.dumps({
        "display_result": display_result,
        "final_response": final_response,
    })
    return f"{_TOOL_TERMINATION_PREFIX}{payload}"


def _decode_tool_termination(result: str) -> tuple[str, str | None]:
    """Decode an optional tool-driven termination payload."""
    if not result.startswith(_TOOL_TERMINATION_PREFIX):
        return result, None

    payload = result[len(_TOOL_TERMINATION_PREFIX):]
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return result, None

    display_result = str(data.get("display_result", ""))
    final_response = str(data.get("final_response", "")).strip()
    return display_result, final_response or display_result


def _build_symbol_preview_with_timeout(
    *,
    project_root: Path,
    working_set: list[str],
    deadline_ms: int = _SYMBOL_PREVIEW_DEADLINE_MS,
) -> str:
    """Run symbol preview behind an outer soft deadline."""
    result: list[str] = []

    def _target() -> None:
        try:
            result.append(build_active_symbol_preview(
                project_root=project_root,
                working_set=working_set,
                deadline_ms=deadline_ms,
            ))
        except Exception:
            logger.debug("Layer 1 symbol preview skipped", exc_info=True)

    thread = threading.Thread(
        target=_target,
        name="autocode-symbol-preview",
        daemon=True,
    )
    thread.start()
    thread.join(deadline_ms / 1000)
    if thread.is_alive():
        return ""
    return result[0] if result else ""


class ToolExecutionOutcome(tuple[str, str | None]):
    """Tool execution result plus an optional loop-termination response."""

    __slots__ = ()

    @property
    def result(self) -> str:
        return self[0]

    @property
    def terminate_final(self) -> str | None:
        return self[1]


class AgentMode(Enum):
    """Execution mode for the agent loop."""
    NORMAL = "normal"
    PLANNING = "planning"
    RESEARCH = "research"
    BUILD = "build"      # Like NORMAL but verification required before completion
    REVIEW = "review"    # Like PLANNING — read-only, produces risk summary


class AgentLoop:
    """Runs the LLM <-> tool execution cycle up to MAX_ITERATIONS."""

    MAX_ITERATIONS = 1000
    MAX_TEXT_NUDGES = 2

    def __init__(
        self,
        provider: Any,
        tool_registry: ToolRegistry,
        approval_manager: ApprovalManager,
        session_store: SessionStore,
        session_id: str,
        memory_content: str | None = None,
        context_engine: ContextEngine | None = None,
        task_store: TaskStore | None = None,
        event_recorder: EventRecorder | None = None,
        subagent_manager: Any | None = None,
        memory_context: str = "",
        token_tracker: Any | None = None,
        session_stats: Any | None = None,
        profiler: Any | None = None,
        middleware: Any | None = None,
        delegation_policy: Any | None = None,
        tool_shim: Any | None = None,
        layer2_config: Any | None = None,
        hook_registry: Any | None = None,
        tool_result_cache: ToolResultCache | None = None,
        tool_result_cache_min_bytes: int = 1024,
        checkpoint_store: Any | None = None,
        project_root: Path | None = None,
        verify_config: AutoVerifyConfig | None = None,
        prompt_cache_keepalive_config: PromptCacheKeepaliveConfig | None = None,
    ) -> None:
        self.provider = provider
        self.tool_registry = tool_registry
        self.approval_manager = approval_manager
        self.session_store = session_store
        self.session_id = session_id
        self._memory_content = memory_content
        self._context_engine = context_engine
        self._task_store = task_store
        self._event_recorder = event_recorder
        self._subagent_manager = subagent_manager
        self._memory_context = memory_context
        self._token_tracker = token_tracker
        self._session_stats = session_stats
        self._profiler = profiler
        self._middleware = middleware
        self._delegation_policy = delegation_policy
        self._tool_shim = tool_shim
        self._layer2_config = layer2_config
        self._hook_registry = hook_registry
        self._tool_result_cache = tool_result_cache
        self._tool_result_cache_min_bytes = tool_result_cache_min_bytes
        self._checkpoint_store = checkpoint_store
        self._project_root = project_root
        self._verify_config = verify_config
        self._prompt_cache_keepalive_config = prompt_cache_keepalive_config
        self._prompt_cache_keepalive: PromptCacheKeepalive | None = None
        self._verification_failure_count = 0
        self._tool_call_idx = 0
        self._hook_session_started = False
        self._current_episode_id: str | None = None
        self._cancelled = False
        self._mode: AgentMode = AgentMode.NORMAL
        # Caching: static prefix and tool schemas don't change mid-session
        self._static_prefix: str | None = None
        self._cached_tool_schemas: list[dict[str, Any]] | None = None
        self._environment_snapshot: str | None = None

    def _ensure_prompt_cache_keepalive(self) -> None:
        """Start provider-gated prompt-cache keepalive for the stable prefix."""
        if self._static_prefix is None:
            return
        if self._prompt_cache_keepalive is not None:
            self._prompt_cache_keepalive.start()
            return
        dashboard = getattr(self._token_tracker, "cost_dashboard", None)
        self._prompt_cache_keepalive = PromptCacheKeepalive(
            provider=self.provider,
            static_prompt=self._static_prefix,
            cost_dashboard=dashboard,
            provider_label=self._token_provider_label(),
            config=self._prompt_cache_keepalive_config,
        )
        self._prompt_cache_keepalive.start()

    def _token_provider_label(self) -> str:
        """Return a stable provider/model label for token and cost reporting."""
        provider_type = type(self.provider).__name__
        model = str(getattr(self.provider, "model", "") or "").strip()
        api_base = str(getattr(self.provider, "api_base", "") or "").lower().rstrip("/")
        provider_type_lower = provider_type.lower()

        if "openrouter" in provider_type_lower or api_base == "http://localhost:4000/v1":
            provider = "openrouter"
        elif "ollama" in provider_type_lower or "11434" in api_base:
            provider = "ollama"
        else:
            return provider_type

        return f"{provider} / {model}" if model else provider

    # ----- Hook lifecycle helpers -----
    # All three wrap hook_registry.fire in a try/except so a broken hook
    # cannot crash the agent loop; any exception is swallowed at DEBUG level.

    def _fire_session_start(self) -> None:
        """Fire SessionStart hooks once per AgentLoop instance.

        The `_hook_session_started` guard prevents re-fires when `run()` is
        called multiple times on the same loop (once per user turn).
        """
        if self._hook_registry is None or self._hook_session_started:
            return
        self._hook_session_started = True
        try:
            self._hook_registry.fire(
                HookEvent.SESSION_START,
                {"session_id": self.session_id},
            )
        except Exception:  # noqa: BLE001
            logger.debug("SessionStart hook run failed", exc_info=True)

    def _fire_pre_tool_use(self, tc: Any) -> str | None:
        """Fire PreToolUse hooks. Return a block reason if blocked, else None."""
        if self._hook_registry is None:
            return None
        try:
            results = self._hook_registry.fire(
                HookEvent.PRE_TOOL_USE,
                {"session_id": self.session_id, "arguments": dict(tc.arguments)},
                tool_name=tc.name,
            )
        except Exception:  # noqa: BLE001
            logger.debug("PreToolUse hook run failed", exc_info=True)
            return None
        for result in results:
            if result.blocked:
                reason = result.block_reason or "hook denied"
                return f"Blocked by PreToolUse hook: {reason}"
        return None

    def _fire_post_tool_use(
        self,
        tc: Any,
        *,
        status: str,
        result: str,
        duration_ms: int,
    ) -> None:
        """Fire PostToolUse hooks after an executed tool call. Advisory only."""
        if self._hook_registry is None:
            return
        try:
            self._hook_registry.fire(
                HookEvent.POST_TOOL_USE,
                {
                    "session_id": self.session_id,
                    "arguments": dict(tc.arguments),
                    "status": status,
                    "result_preview": result[:200] if result else "",
                    "duration_ms": duration_ms,
                },
                tool_name=tc.name,
            )
        except Exception:  # noqa: BLE001
            logger.debug("PostToolUse hook run failed", exc_info=True)

    def _fire_stop(
        self, final_text: str, *, outcome: str, failure: bool = False,
    ) -> None:
        """Fire Stop or StopFailure hooks at end of turn. Advisory only."""
        if self._hook_registry is None:
            return
        try:
            event = HookEvent.STOP_FAILURE if failure else HookEvent.STOP
            self._hook_registry.fire(
                event,
                {
                    "session_id": self.session_id,
                    "outcome": outcome,
                    "final_text_preview": final_text[:200] if final_text else "",
                },
            )
        except Exception:  # noqa: BLE001
            logger.debug("Stop hook run failed", exc_info=True)

    def _record_tool_result_cache_entry(
        self,
        tc: ToolCall,
        result: str,
    ) -> None:
        """Record large successful tool results for later selective clearing."""
        if self._tool_result_cache is None:
            return
        if tc.name in CACHE_MANAGEMENT_TOOL_NAMES:
            return
        result_size = len(result.encode("utf-8", errors="replace"))
        if result_size < self._tool_result_cache_min_bytes:
            return
        self._tool_result_cache.record(tc.name, tc.arguments, result)

    def _resolve_project_root(self) -> Path:
        """Resolve the project root from explicit config, session metadata, or cwd."""
        try:
            if self._project_root:
                return self._project_root
        except Exception:
            pass
        try:
            session = self.session_store.get_session(self.session_id)
            if session and session.project_dir:
                return Path(session.project_dir)
        except Exception:
            pass
        return Path.cwd()

    @staticmethod
    def _extract_touched_files(tool_name: str, arguments: dict[str, Any]) -> list[str]:
        """Extract file paths from tool arguments for FS-mutating tools."""
        paths: list[str] = []
        if tool_name in ("write_file", "edit_file") and "path" in arguments:
            paths.append(str(arguments["path"]))
        elif tool_name == "apply_patch":
            if "path" in arguments:
                paths.append(str(arguments["path"]))
            elif "patches" in arguments and isinstance(arguments["patches"], list):
                for patch in arguments["patches"]:
                    if isinstance(patch, dict) and "path" in patch:
                        paths.append(str(patch["path"]))
        return paths

    def _build_environment_snapshot(self) -> str:
        """Build a compact one-time workspace snapshot for iteration zero."""
        root = self._resolve_project_root()
        if self._environment_snapshot is None:
            lines = [f"- Project root: {root}"]

            try:
                entries = sorted(root.iterdir(), key=lambda entry: entry.name.lower())
                preview = [
                    entry.name + ("/" if entry.is_dir() else "")
                    for entry in entries[:10]
                ]
                if preview:
                    suffix = " ..." if len(entries) > len(preview) else ""
                    lines.append(f"- Top-level entries: {', '.join(preview)}{suffix}")
            except OSError:
                lines.append("- Top-level entries: unavailable")

            try:
                branch = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=2,
                    check=False,
                )
                if branch.returncode == 0:
                    branch_name = branch.stdout.strip() or "(detached)"
                    status = subprocess.run(
                        ["git", "status", "--short", "--untracked-files=no"],
                        cwd=root,
                        capture_output=True,
                        text=True,
                        timeout=2,
                        check=False,
                    )
                    dirty_count = len([line for line in status.stdout.splitlines() if line.strip()])
                    lines.append(f"- Git branch: {branch_name} ({dirty_count} tracked changes)")
            except (OSError, subprocess.SubprocessError):
                lines.append("- Git branch: unavailable")

            layer2_enabled = True
            if self._layer2_config is not None:
                layer2_enabled = bool(getattr(self._layer2_config, "enabled", True))

            if layer2_enabled:
                try:
                    from autocode.agent.tools import get_code_index_cache_stats

                    stats = get_code_index_cache_stats(str(root))
                    if stats is not None:
                        lines.append(
                            "- Retrieval index: warm, "
                            f"{stats['files_indexed']} files indexed, "
                            f"{stats['total_chunks']} chunks cached"
                        )
                    else:
                        lines.append(
                            "- Retrieval index: cold; synchronous warmup deferred "
                            "until an explicit retrieval request"
                        )
                except Exception as exc:
                    logger.debug("Layer2 warmup skipped: %s", exc)

            tool_names = [tool.name for tool in self.tool_registry.get_all()]
            if tool_names:
                tools_preview = ", ".join(tool_names[:8])
                if len(tool_names) > 8:
                    tools_preview += ", ..."
                lines.append(f"- Available tools: {tools_preview}")

            self._environment_snapshot = "\n".join(lines)

        snapshot = self._environment_snapshot
        try:
            from autocode.agent.tools import get_active_working_set

            working_set = get_active_working_set(str(root), limit=5)
            if working_set:
                snapshot += "\n- Active working set: " + ", ".join(working_set)
                symbol_preview = _build_symbol_preview_with_timeout(
                    project_root=root,
                    working_set=working_set,
                )
                if symbol_preview:
                    snapshot += "\n" + symbol_preview
        except Exception:
            pass
        return snapshot

    def _build_middleware_metadata(self, user_message: str) -> dict[str, Any]:
        """Build per-iteration metadata for middleware decisions."""
        has_tasks = bool(self._task_store and self._task_store.list_tasks())
        task_tool_names = {"create_task", "update_task", "list_tasks", "add_task_dependency"}
        has_task_tools = all(self.tool_registry.get(name) is not None for name in task_tool_names)
        return {
            "session_id": self.session_id,
            "user_message": user_message,
            "has_tasks": has_tasks,
            "has_task_tools": has_task_tools,
            "plan_mode": self._mode == AgentMode.PLANNING,
            "agent_mode": self._mode.value,
            "read_only_mode": self._mode in {
                AgentMode.PLANNING, AgentMode.RESEARCH, AgentMode.REVIEW
            },
            "build_mode": self._mode == AgentMode.BUILD,
            "review_mode": self._mode == AgentMode.REVIEW,
            "environment_snapshot": self._build_environment_snapshot(),
        }

    def set_mode(self, mode: AgentMode) -> None:
        """Set the agent execution mode (normal or planning)."""
        self._mode = mode
        logger.info("Agent mode set to %s", mode.value)

    def get_mode(self) -> AgentMode:
        """Get the current agent execution mode."""
        return self._mode

    def _run_middleware(self, event: str, **kwargs: Any) -> Any | None:
        """Run a middleware hook and return its context if middleware is enabled."""
        if not self._middleware:
            return None

        from autocode.agent.middleware import MiddlewareContext

        ctx = MiddlewareContext(**kwargs)
        return self._middleware.run(event, ctx)

    def _build_system_prompt(self) -> str:
        """Build the system prompt with current runtime state.

        Caches the static prefix on first call; only rebuilds the
        dynamic suffix each iteration.
        """
        if self._static_prefix is None:
            self._static_prefix = build_static_prefix()

        task_summary = ""
        if self._task_store:
            task_summary = self._task_store.summary()
        subagent_status = ""
        if self._subagent_manager and hasattr(self._subagent_manager, "get_status_summary"):
            subagent_status = self._subagent_manager.get_status_summary()
        dynamic = build_dynamic_suffix(
            self._memory_content,
            shell_enabled=self.approval_manager.shell_config.enabled,
            approval_mode=self.approval_manager.mode.value,
            task_summary=task_summary,
            subagent_status=subagent_status,
            agent_mode=self._mode.value,
            memory_context=self._memory_context,
        )
        return self._static_prefix + dynamic

    def cancel(self) -> None:
        """Cancel the current run."""
        self._cancelled = True

    async def run(
        self,
        user_message: str,
        *,
        on_chunk: Callable[[str], None] | None = None,
        on_thinking_chunk: Callable[[str], None] | None = None,
        on_retry_notice: Callable[[str], None] | None = None,
        on_tool_call: Callable[[str, str, str], None] | None = None,
        approval_callback: Callable[[str, dict[str, Any]], Awaitable[bool]] | None = None,
        ask_user_callback: Callable[[str, list[str], bool], Awaitable[str]] | None = None,
        reasoning_enabled: bool = True,
        injected_context: str = "",
    ) -> str:
        """Run the agent loop for a user message.

        Args:
            user_message: The user's input text.
            on_chunk: Called with text chunks as they stream.
            on_thinking_chunk: Called with thinking/reasoning chunks.
            on_retry_notice: Called with non-fatal retry/degraded upstream notices.
            on_tool_call: Called with (tool_name, status, result) for display.
            approval_callback: Async callable for user approval. Returns bool.
            ask_user_callback: Async callable when the LLM invokes ask_user.
                Receives (question, options, allow_text), returns user's answer.
            reasoning_enabled: User/session-level gate for provider reasoning.
                Middleware may reduce this per iteration, but cannot re-enable it.

        Returns:
            The final assistant text response.
        """
        self._cancelled = False
        _run_start = time.monotonic()
        logger.debug("AgentLoop.run start: %s", user_message[:80])

        self._fire_session_start()

        # Store user message
        self.session_store.add_message(self.session_id, "user", user_message)

        # Training-grade episode tracking
        if self._event_recorder:
            self._current_episode_id = self._event_recorder.on_turn_start(user_message)
        _episode_id = self._current_episode_id

        # Build messages from session history (rebuild prompt for current state)
        # Use core schemas only to reduce token usage; deferred tools
        # are discoverable via the tool_search meta-tool.
        # Cache tool schemas since they don't change mid-session.
        if self._cached_tool_schemas is None:
            self._cached_tool_schemas = self.tool_registry.get_core_schemas_openai_format()
            if self._task_store:
                core_names = {
                    schema["function"]["name"]
                    for schema in self._cached_tool_schemas
                    if schema.get("type") == "function"
                }
                for tool in self.tool_registry.get_all():
                    if tool.name in {
                        "create_task", "update_task", "list_tasks", "add_task_dependency",
                    } and tool.name not in core_names:
                        self._cached_tool_schemas.append({
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description,
                                "parameters": tool.parameters,
                            },
                        })
        tool_schemas = self._cached_tool_schemas
        # Ensure static prefix is cached
        if self._static_prefix is None:
            self._static_prefix = build_static_prefix()
        self._ensure_prompt_cache_keepalive()

        if self._context_engine:
            task_summary = self._task_store.summary() if self._task_store else ""
            system_prompt = self._build_system_prompt()

            def _before_compaction() -> bool:
                ctx = self._run_middleware(
                    "before_compaction",
                    messages=[{"role": "system", "content": system_prompt}],
                    metadata={"session_id": self.session_id},
                )
                return False if ctx and ctx.skip else True

            def _after_compaction(summary: str) -> None:
                self._run_middleware(
                    "after_compaction",
                    metadata={"session_id": self.session_id, "summary": summary},
                )

            # Compute dynamic suffix for cache_control splitting
            subagent_status = ""
            if self._subagent_manager and hasattr(self._subagent_manager, "get_status_summary"):
                subagent_status = self._subagent_manager.get_status_summary()
            dynamic = build_dynamic_suffix(
                self._memory_content,
                shell_enabled=self.approval_manager.shell_config.enabled,
                approval_mode=self.approval_manager.mode.value,
                task_summary=task_summary,
                subagent_status=subagent_status,
                agent_mode=self._mode.value,
                memory_context=self._memory_context,
            )

            if self._profiler:
                self._profiler.start("context-build")
            try:
                messages = await self._context_engine.build_messages(
                    self.session_id,
                    system_prompt,
                    tool_schemas,
                    task_summary=task_summary,
                    before_compaction=_before_compaction if self._middleware else None,
                    after_compaction=_after_compaction if self._middleware else None,
                    static_prefix=self._static_prefix,
                    dynamic_suffix=dynamic,
                )
            finally:
                if self._profiler:
                    self._profiler.stop("context-build", "context")
        else:
            messages = [
                {"role": "system", "content": self._build_system_prompt()},
            ]
            for msg in self.session_store.get_messages(self.session_id):
                if msg.role in ("user", "assistant", "system", "tool"):
                    messages.append({"role": msg.role, "content": msg.content})
        if injected_context:
            messages.insert(1, {"role": "system", "content": injected_context})
        logger.debug("Loaded %d tool schemas, %d messages", len(tool_schemas), len(messages))
        log_event(
            logger, logging.INFO, "agent_loop_start",
            session_id=self.session_id,
            user_message_length=len(user_message),
            message_count=len(messages),
            tool_count=len(tool_schemas),
        )

        _text_nudge_count = 0
        _todo_write_seen = False  # Track if agent has planned via todo_write

        for _iteration in range(self.MAX_ITERATIONS):
            # Middleware: on_iteration
            self._run_middleware("on_iteration", iteration=_iteration)

            if self._cancelled:
                logger.debug("Cancelled at iteration %d", _iteration)
                if self._event_recorder and _episode_id:
                    self._event_recorder.on_turn_end(_episode_id, "[Cancelled]", "cancelled", {})
                return "[Cancelled]"

            # Call LLM with tools
            logger.debug("Iteration %d: calling generate_with_tools", _iteration)
            log_event(
                logger, logging.INFO, "llm_request",
                session_id=self.session_id,
                iteration=_iteration,
                provider=getattr(self.provider, "model", "unknown"),
            )
            if self._event_recorder and _episode_id:
                self._event_recorder.on_model_request(
                    _episode_id, messages, tool_schemas, _iteration,
                )
            # Middleware: before_model
            _mw_ctx = self._run_middleware(
                "before_model",
                iteration=_iteration,
                messages=messages,
                metadata=self._build_middleware_metadata(user_message),
            )
            if _mw_ctx and _mw_ctx.skip:
                break
            if _mw_ctx and _mw_ctx.messages is not messages:
                messages = _mw_ctx.messages
            effective_reasoning_enabled = reasoning_enabled
            if _mw_ctx:
                effective_reasoning_enabled = (
                    reasoning_enabled
                    and bool(_mw_ctx.metadata.get("_reasoning_enabled", True))
                )

            _llm_start = time.monotonic()
            if self._profiler:
                self._profiler.start(f"llm-{_iteration}")
            try:
                response: LLMResponse = await self.provider.generate_with_tools(
                    messages, tool_schemas,
                    on_chunk=on_chunk,
                    on_thinking_chunk=on_thinking_chunk,
                    on_retry_notice=on_retry_notice,
                    reasoning_enabled=effective_reasoning_enabled,
                )
            finally:
                if self._profiler:
                    self._profiler.stop(f"llm-{_iteration}", "llm", iteration=_iteration)
            _llm_ms = int((time.monotonic() - _llm_start) * 1000)
            logger.debug(
                "LLM response: content=%s, tool_calls=%d, reasoning=%s",
                bool(response.content), len(response.tool_calls), bool(response.reasoning),
            )
            log_event(
                logger, logging.INFO, "llm_response",
                session_id=self.session_id,
                iteration=_iteration,
                duration_ms=_llm_ms,
                content_length=len(response.content or ""),
                tool_calls_count=len(response.tool_calls),
                finish_reason=response.finish_reason,
            )
            if self._event_recorder and _episode_id:
                self._event_recorder.on_model_response(
                    _episode_id, response, _llm_ms, _iteration,
            )
            # Track token usage
            if self._token_tracker and response.usage:
                provider_name = self._token_provider_label()
                self._token_tracker.record(
                    prompt_tokens=response.usage.get("prompt_tokens", 0),
                    completion_tokens=response.usage.get("completion_tokens", 0),
                    provider=provider_name,
                    cached_input_tokens=response.usage.get("cached_input_tokens", 0),
                )
            else:
                log_debug_prompt(self.session_id, messages, response)

            # Tool shim: extract tool calls from text if model doesn't
            # support native tool calling (Goose TOOLSHIM pattern)
            if not response.tool_calls and response.content and self._tool_shim:
                shimmed = self._tool_shim.extract(response.content)
                if shimmed:
                    response.tool_calls = [
                        ToolCall(
                            id=f"shim-{i}",
                            name=s.name,
                            arguments=s.arguments,
                        )
                        for i, s in enumerate(shimmed)
                    ]

            _after_model_ctx = self._run_middleware(
                "after_model",
                iteration=_iteration,
                messages=messages,
                response=response,
                metadata=self._build_middleware_metadata(user_message),
            )
            if _after_model_ctx and _after_model_ctx.skip:
                break
            if _after_model_ctx and _after_model_ctx.response is not None:
                response = _after_model_ctx.response
            if _after_model_ctx:
                forced_retry = _after_model_ctx.metadata.get("_force_retry_user_message")
                if forced_retry:
                    if response.content:
                        messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": str(forced_retry)})
                    if self._middleware and hasattr(self._middleware, "shared_state"):
                        self._middleware.shared_state["_force_retry_user_message"] = None
                    continue

            # If text-only response (no tool calls)
            if not response.tool_calls:
                text = response.content or ""
                empty_response = not text

                # In AUTO mode, nudge the model to use tools instead of just talking
                if (
                    self.approval_manager.mode == ApprovalMode.AUTO
                    and _text_nudge_count < self.MAX_TEXT_NUDGES
                ):
                    _text_nudge_count += 1
                    logger.debug(
                        "No-tool nudge %d/%d in AUTO mode (empty=%s)",
                        _text_nudge_count, self.MAX_TEXT_NUDGES,
                        empty_response,
                    )
                    if text:
                        messages.append({"role": "assistant", "content": text})
                    messages.append({
                        "role": "user",
                        "content": (
                            "Your previous response "
                            + (
                                "was empty and did not call any tools. "
                                if empty_response
                                else "did not call any tools. "
                            )
                            + "You must call tools to make changes. "
                            "Do not just describe the fix — call a tool now."
                        ),
                    })
                    continue

                if empty_response:
                    text = (
                        "Provider returned an empty response without tool calls. "
                        "Try again or switch model/provider."
                    )

                # BUILD mode hard verification gate: block completion
                # unless verification evidence is satisfied
                if (
                    self._mode == AgentMode.BUILD
                    and self._middleware
                    and hasattr(self._middleware, "shared_state")
                ):
                    ss = self._middleware.shared_state
                    if ss.get("_verification_needed") and not ss.get("_verification_satisfied"):
                        retries = ss.get("_build_gate_retries", 0)
                        if retries < 3:
                            ss["_build_gate_retries"] = retries + 1
                            logger.info(
                                "BUILD gate: blocking completion, verification needed (retry %d/3)",
                                retries + 1,
                            )
                            if text:
                                messages.append({"role": "assistant", "content": text})
                            messages.append({
                                "role": "user",
                                "content": (
                                    "[BUILD MODE] You cannot finish without verification. "
                                    "Run tests or a verification command now to prove your "
                                    "changes work. Use run_command with pytest, verify.sh, "
                                    "or an appropriate check."
                                ),
                            })
                            continue
                        else:
                            logger.warning(
                                "BUILD gate: retries exhausted,"
                                " allowing completion without verification"
                            )

                self.session_store.add_message(self.session_id, "assistant", text)
                logger.debug("Text-only response, returning (%d chars)", len(text))
                _total_ms = int((time.monotonic() - _run_start) * 1000)
                log_event(
                    logger, logging.INFO, "agent_loop_end",
                    session_id=self.session_id,
                    iterations=_iteration + 1,
                    total_duration_ms=_total_ms,
                    outcome="empty_response" if empty_response else "text_response",
                )
                if self._event_recorder and _episode_id:
                    self._event_recorder.on_turn_end(
                        _episode_id,
                        text,
                        "empty_response" if empty_response else "text_response",
                        {"iterations": _iteration + 1, "total_duration_ms": _total_ms},
                    )
                return text

            # Process tool calls
            # First, add assistant message with tool calls to history
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": response.content or ""}
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                }
                for tc in response.tool_calls
            ]
            messages.append(assistant_msg)

            msg_id = self.session_store.add_message(
                self.session_id, "assistant", response.content or "(tool calls)"
            )

            for tc in response.tool_calls:
                # Track todo_write usage for mandatory planning
                if tc.name == "todo_write":
                    _todo_write_seen = True
                outcome = await self._execute_tool_call(
                    tc, msg_id,
                    on_tool_call=on_tool_call,
                    approval_callback=approval_callback,
                    ask_user_callback=ask_user_callback,
                )
                # Add tool result to messages for the next iteration
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": outcome.result,
                })
                if outcome.terminate_final is not None:
                    final_text = outcome.terminate_final
                    self.session_store.add_message(
                        self.session_id, "assistant", final_text,
                    )
                    _total_ms = int((time.monotonic() - _run_start) * 1000)
                    log_event(
                        logger, logging.INFO, "agent_loop_end",
                        session_id=self.session_id,
                        iterations=_iteration + 1,
                        total_duration_ms=_total_ms,
                        outcome="tool_terminated",
                    )
                    if self._event_recorder and _episode_id:
                        self._event_recorder.on_turn_end(
                            _episode_id, final_text, "tool_terminated",
                            {"iterations": _iteration + 1, "total_duration_ms": _total_ms},
                        )
                    self._fire_stop(final_text, outcome="tool_terminated")
                    return final_text

            # Nudge: if iteration 2+ and no todo_write yet, inject planning prompt
            if (
                _iteration == 1
                and not _todo_write_seen
                and self.tool_registry.get("todo_write") is not None
                and self.approval_manager.mode == ApprovalMode.AUTO
            ):
                messages.append({
                    "role": "user",
                    "content": (
                        "[Planning Required] You have not created a plan yet. "
                        "Before making more changes, call todo_write to outline "
                        "your approach as a checklist. This helps track progress "
                        "and avoid rework."
                    ),
                })

        # Max iterations reached — get final text response without tools
        log_event(
            logger, logging.WARNING, "agent_loop_max_iterations",
            session_id=self.session_id,
            iterations=self.MAX_ITERATIONS,
        )
        final_text = response.content or "[Max iterations reached]"
        self.session_store.add_message(self.session_id, "assistant", final_text)
        _total_ms = int((time.monotonic() - _run_start) * 1000)
        log_event(
            logger, logging.INFO, "agent_loop_end",
            session_id=self.session_id,
            iterations=self.MAX_ITERATIONS,
            total_duration_ms=_total_ms,
            outcome="max_iterations",
        )
        if self._event_recorder and _episode_id:
            self._event_recorder.on_turn_end(
                _episode_id, final_text, "max_iterations",
                {"iterations": self.MAX_ITERATIONS, "total_duration_ms": _total_ms},
            )
        self._fire_stop(final_text, outcome="max_iterations", failure=True)
        return final_text

    async def _handle_ask_user(
        self,
        tc: ToolCall,
        msg_id: int,
        *,
        on_tool_call: Callable[[str, str, str], None] | None = None,
        callback: Callable[[str, list[str], bool], Awaitable[str]] | None = None,
    ) -> ToolExecutionOutcome:
        """Handle the ask_user tool call via interactive callback."""
        question = tc.arguments.get("question", "")
        options = tc.arguments.get("options", [])
        allow_text = tc.arguments.get("allow_text", False)
        logger.debug("ask_user: q=%s, opts=%s, text=%s", question[:50], options, allow_text)

        if on_tool_call:
            on_tool_call(tc.name, "waiting", question)

        if self.approval_manager.mode == ApprovalMode.AUTONOMOUS:
            result = (
                "Blocked in autonomous mode: ask_user is disabled. "
                "Use the available context and tools to continue without user interaction."
            )
            if on_tool_call:
                on_tool_call(tc.name, "blocked", result)
            return ToolExecutionOutcome((result, None))

        if callback is None:
            result = "ask_user requires an interactive UI (no callback provided)."
            if on_tool_call:
                on_tool_call(tc.name, "error", result)
            return ToolExecutionOutcome((result, None))

        # Record tool call
        tc_row_id = self.session_store.add_tool_call(
            session_id=self.session_id,
            message_id=msg_id,
            tool_call_id=tc.id,
            tool_name=tc.name,
            arguments=tc.arguments,
            status="waiting",
        )

        try:
            response = await callback(question, options, allow_text)
            response_str = str(response) if response else "(no response from user)"
            self.session_store.update_tool_call(
                tc_row_id, result=response_str, status="completed", duration_ms=0,
            )
            self.session_store.add_message(
                self.session_id, "tool", f"[ask_user] User answered: {response_str}",
            )
            if self._event_recorder and self._current_episode_id:
                self._event_recorder.on_human_feedback(
                    self._current_episode_id, "ask_user_response", response_str,
                )
            if on_tool_call:
                on_tool_call(tc.name, "completed", response_str)
            return ToolExecutionOutcome((f"User responded: {response_str}", None))
        except Exception as e:
            error = f"Error in ask_user: {e}"
            self.session_store.update_tool_call(
                tc_row_id, result=error, status="error", duration_ms=0,
            )
            if on_tool_call:
                on_tool_call(tc.name, "error", error)
            return ToolExecutionOutcome((error, None))

    async def _invoke_tool_handler(
        self,
        tool: Any,
        arguments: dict[str, Any],
    ) -> tuple[str, bool]:
        """Run a tool handler and return (result, cancel_after_completion)."""
        raw_result: Any | None = None
        try:
            raw_result = tool.handler(**arguments)
            if not inspect.isawaitable(raw_result):
                return raw_result, False

            handler_task = asyncio.ensure_future(raw_result)
            raw_result = None
            if tool.interruptible:
                try:
                    return await handler_task, False
                except asyncio.CancelledError:
                    handler_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await handler_task
                    raise

            try:
                return await asyncio.shield(handler_task), False
            except asyncio.CancelledError:
                result = await handler_task
                return result, True
        except BaseException:
            if inspect.iscoroutine(raw_result):
                raw_result.close()
            raise

    async def _execute_tool_call(
        self,
        tc: ToolCall,
        msg_id: int,
        *,
        on_tool_call: Callable[[str, str, str], None] | None = None,
        approval_callback: Callable[[str, dict[str, Any]], Awaitable[bool]] | None = None,
        ask_user_callback: Callable[[str, list[str], bool], Awaitable[str]] | None = None,
    ) -> ToolExecutionOutcome:
        """Execute a single tool call with approval checking."""
        # Special handling for ask_user — route to interactive callback
        if tc.name == "ask_user":
            logger.debug("Routing to ask_user handler")
            return await self._handle_ask_user(
                tc, msg_id, on_tool_call=on_tool_call, callback=ask_user_callback,
            )

        # PreToolUse hooks can abort the tool call via blocking result.
        blocking = self._fire_pre_tool_use(tc)
        if blocking is not None:
            if on_tool_call:
                on_tool_call(tc.name, "blocked", blocking)
            return ToolExecutionOutcome((blocking, None))

        logger.debug("Executing tool: %s(%s)", tc.name, list(tc.arguments.keys()))
        if self._event_recorder and self._current_episode_id:
            self._event_recorder.on_tool_call(
                self._current_episode_id, tc.name, tc.arguments, tc.id,
            )
        log_event(
            logger, logging.INFO, "tool_call_start",
            session_id=self.session_id,
            tool_name=tc.name,
            argument_keys=list(tc.arguments.keys()),
        )
        tool = self.tool_registry.get(tc.name)
        if tool is None:
            # Check if it's a deferred tool the LLM tried to call without
            # schemas being sent.  Suggest tool_search so the model can
            # discover and properly invoke it on the next turn.
            deferred = self.tool_registry.get_deferred_tool_names()
            if tc.name in deferred:
                error = (
                    f"Tool '{tc.name}' exists but its schema was not loaded. "
                    f"Use tool_search(query=\"{tc.name}\") to load it first."
                )
            else:
                error = f"Unknown tool: {tc.name}"
            if on_tool_call:
                on_tool_call(tc.name, "error", error)
            return ToolExecutionOutcome((error, None))

        if tc.name == "spawn_subagent" and self._delegation_policy is not None:
            role = {
                "explore": "scout",
                "plan": "architect",
                "execute": "engineer",
            }.get(str(tc.arguments.get("subagent_type", "")), "subagent")
            allowed, reason = self._delegation_policy.can_spawn(role)
            if not allowed:
                blocked_result = (
                    f"Blocked: Delegation policy rejected spawn_subagent ({reason})."
                )
                if on_tool_call:
                    on_tool_call(tc.name, "blocked", blocked_result)
                return ToolExecutionOutcome((blocked_result, None))

        # Read-only modes: block tools with mutates_fs or executes_shell
        if self._mode in {AgentMode.PLANNING, AgentMode.RESEARCH, AgentMode.REVIEW}:
            if tool and (tool.mutates_fs or tool.executes_shell):
                if self._mode == AgentMode.PLANNING:
                    reason = (
                        f"Blocked in plan mode: {tc.name} modifies filesystem or "
                        "executes shell. Use /plan approve to switch to execution mode."
                    )
                elif self._mode == AgentMode.REVIEW:
                    reason = (
                        f"Blocked in review mode: {tc.name} modifies filesystem or "
                        "executes shell. Review is read-only — use /review off to exit."
                    )
                else:
                    reason = (
                        f"Blocked in research mode: {tc.name} modifies filesystem or "
                        "executes shell. Use /research off to switch to execution mode."
                    )
                log_event(
                    logger, logging.INFO, "tool_blocked_plan_mode",
                    session_id=self.session_id, tool_name=tc.name,
                )
                if on_tool_call:
                    on_tool_call(tc.name, "blocked", reason)
                return ToolExecutionOutcome((reason, None))

        # Check if blocked
        blocked, reason = self.approval_manager.is_blocked(tc.name, tc.arguments)
        if blocked:
            log_event(
                logger, logging.WARNING, "tool_blocked",
                session_id=self.session_id, tool_name=tc.name, reason=reason,
            )
            if on_tool_call:
                on_tool_call(tc.name, "blocked", reason)
            return ToolExecutionOutcome((f"Blocked: {reason}", None))

        # Check if write is blocked in read-only mode
        if self.approval_manager.is_write_blocked(tc.name):
            reason = "Write operations are not allowed in read-only mode."
            if on_tool_call:
                on_tool_call(tc.name, "blocked", reason)
            return ToolExecutionOutcome((f"Blocked: {reason}", None))

        # Check if shell needs enabling (soft block — user can approve)
        shell_needs_enabling = (
            tc.name == "run_command"
            and self.approval_manager.is_shell_disabled()
        )
        if shell_needs_enabling and self.approval_manager.mode == ApprovalMode.AUTONOMOUS:
            reason = (
                "Blocked in autonomous mode: shell execution is disabled. "
                "Enable shell before starting a non-interactive run."
            )
            if on_tool_call:
                on_tool_call(tc.name, "blocked", reason)
            return ToolExecutionOutcome((reason, None))

        # Check approval (merged with shell-enable prompt)
        if self.approval_manager.needs_approval(tool) or shell_needs_enabling:
            if approval_callback:
                approved = await approval_callback(tc.name, tc.arguments)
                if not approved:
                    log_event(
                        logger, logging.WARNING, "tool_denied",
                        session_id=self.session_id, tool_name=tc.name,
                    )
                    if self._event_recorder and self._current_episode_id:
                        self._event_recorder.on_human_feedback(
                            self._current_episode_id, "denial", tc.name,
                        )
                    if on_tool_call:
                        on_tool_call(tc.name, "denied", "User denied")
                    return ToolExecutionOutcome(("Tool call denied by user.", None))
                if self._event_recorder and self._current_episode_id:
                    self._event_recorder.on_human_feedback(
                        self._current_episode_id, "approval", tc.name,
                    )
                # Enable shell if user approved a shell command
                if shell_needs_enabling:
                    self.approval_manager.enable_shell()
            else:
                # No callback, deny by default for safety
                if on_tool_call:
                    on_tool_call(tc.name, "denied", "No approval callback")
                return ToolExecutionOutcome((
                    "Tool call requires approval but no callback provided.", None,
                ))

        # Record tool call
        tc_row_id = self.session_store.add_tool_call(
            session_id=self.session_id,
            message_id=msg_id,
            tool_call_id=tc.id,
            tool_name=tc.name,
            arguments=tc.arguments,
            status="running",
        )

        if on_tool_call:
            on_tool_call(tc.name, "running", "")

        # Middleware: before_tool
        _tool_ctx = self._run_middleware(
            "before_tool",
            tool_name=tc.name,
            tool_args=tc.arguments,
            metadata={"session_id": self.session_id},
        )
        if _tool_ctx and _tool_ctx.skip:
            result = _tool_ctx.modified_result or "Tool call blocked by middleware"
            self.session_store.update_tool_call(
                tc_row_id, result=result, status="blocked",
            )
            if on_tool_call:
                on_tool_call(tc.name, "blocked", result)
            return ToolExecutionOutcome((result, None))

        # Per-tool checkpoint: snapshot files before FS-mutating tools
        if (
            tool
            and tool.mutates_fs
            and self._checkpoint_store
            and self._project_root
            and self._task_store
        ):
            try:
                from autocode.session.file_snapshot import snapshot_files
                touched = self._extract_touched_files(tc.name, tc.arguments)
                if touched:
                    snap_dir = Path.home() / ".autocode" / "snapshots" / self.session_id / tc.id
                    snap_dir.mkdir(parents=True, exist_ok=True)
                    snapshot_files(self._project_root, snap_dir, touched)
                    self._checkpoint_store.save_per_tool_checkpoint(
                        self._task_store,
                        tool_call_id=tc.id,
                        tool_name=tc.name,
                        tool_call_idx=self._tool_call_idx,
                        kind="pre_tool",
                        files_touched=touched,
                        label=f"pre {tc.name}",
                    )
                    self._tool_call_idx += 1
            except Exception:
                logger.debug("Per-tool checkpoint failed (non-blocking)", exc_info=True)

        # Execute
        start = time.monotonic()
        profile_name = f"tool-{tc.id}"
        if self._profiler:
            self._profiler.start(profile_name)
        try:
            raw_result, cancel_after_completion = await self._invoke_tool_handler(
                tool, tc.arguments,
            )
            result, terminate_final = _decode_tool_termination(raw_result)
            task_tools = {"create_task", "update_task", "add_task_dependency", "list_tasks"}
            if self._context_engine and tc.name not in task_tools:
                result = self._context_engine.truncate_tool_result(
                    result,
                    max_tokens=tool.output_budget_tokens,
                )
            # Track tool usage and file changes in session stats
            if self._session_stats:
                self._session_stats.record_tool_use(tc.name)
                if tc.name in ("write_file", "edit_file") and "path" in tc.arguments:
                    self._session_stats.record_file_change(tc.arguments["path"])
            if tool and tool.mutates_fs and self._project_root:
                staging_note = self._stage_successful_edit(tc, result)
                if staging_note:
                    result = f"{result}\n\n{staging_note}"
                verification_note = await self._verify_successful_edit(tc)
                if verification_note:
                    result = f"{result}\n\n{verification_note}"
            duration_ms = int((time.monotonic() - start) * 1000)
            if self._profiler:
                self._profiler.stop(profile_name, "tool", tool_name=tc.name)
            # Middleware: after_tool
            _after_ctx = self._run_middleware(
                "after_tool",
                tool_name=tc.name,
                tool_args=tc.arguments,
                tool_result=result,
                metadata={"session_id": self.session_id},
            )
            if _after_ctx and _after_ctx.modified_result is not None:
                result = _after_ctx.modified_result
            self._record_tool_result_cache_entry(tc, result)
            self.session_store.update_tool_call(
                tc_row_id, result=result, status="completed", duration_ms=duration_ms,
            )
            log_event(
                logger, logging.INFO, "tool_call_end",
                session_id=self.session_id, tool_name=tc.name,
                duration_ms=duration_ms, status="completed",
            )
            if self._event_recorder and self._current_episode_id:
                self._event_recorder.on_tool_result(
                    self._current_episode_id, tc.name, result, "completed", duration_ms,
                )
            if on_tool_call:
                on_tool_call(tc.name, "completed", result)
            self._fire_post_tool_use(
                tc,
                status="completed",
                result=result,
                duration_ms=duration_ms,
            )

            # Also persist tool result as a message for session history
            self.session_store.add_message(
                self.session_id, "tool", f"[{tc.name}] {result[:500]}"
            )
            if cancel_after_completion:
                raise asyncio.CancelledError
            return ToolExecutionOutcome((result, terminate_final))
        except asyncio.CancelledError:
            duration_ms = int((time.monotonic() - start) * 1000)
            if self._profiler:
                self._profiler.stop(profile_name, "tool", tool_name=tc.name, error=True)
            if tool.interruptible:
                result = "Tool call cancelled."
                self.session_store.update_tool_call(
                    tc_row_id, result=result, status="cancelled", duration_ms=duration_ms,
                )
                log_event(
                    logger, logging.INFO, "tool_call_end",
                    session_id=self.session_id, tool_name=tc.name,
                    duration_ms=duration_ms, status="cancelled",
                )
                if self._event_recorder and self._current_episode_id:
                    self._event_recorder.on_tool_result(
                        self._current_episode_id, tc.name, result, "cancelled", duration_ms,
                    )
                if on_tool_call:
                    on_tool_call(tc.name, "cancelled", result)
                self._fire_post_tool_use(
                    tc,
                    status="cancelled",
                    result=result,
                    duration_ms=duration_ms,
                )
            raise
        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            if self._profiler:
                self._profiler.stop(profile_name, "tool", tool_name=tc.name, error=True)
            error = f"Error: {e}"
            # Middleware: on_error
            _err_ctx = self._run_middleware(
                "on_error",
                tool_name=tc.name,
                tool_args=tc.arguments,
                error=e,
                metadata={"session_id": self.session_id},
            )
            if _err_ctx and _err_ctx.modified_result is not None:
                error = _err_ctx.modified_result
            self.session_store.update_tool_call(
                tc_row_id, result=error, status="error", duration_ms=duration_ms,
            )
            log_event(
                logger, logging.WARNING, "tool_call_end",
                session_id=self.session_id, tool_name=tc.name,
                duration_ms=duration_ms, status="error",
            )
            if self._event_recorder and self._current_episode_id:
                self._event_recorder.on_tool_result(
                    self._current_episode_id, tc.name, error, "error", duration_ms,
                )
            if on_tool_call:
                on_tool_call(tc.name, "error", error)
            self._fire_post_tool_use(
                tc,
                status="error",
                result=error,
                duration_ms=duration_ms,
            )
            return ToolExecutionOutcome((error, None))

    def _stage_successful_edit(self, tc: ToolCall, result: str) -> str:
        """Stage files touched by a successful mutating tool call."""
        if not self._project_root:
            return ""
        touched = self._extract_touched_files(tc.name, tc.arguments)
        if not touched:
            return ""
        try:
            staging = stage_post_edit(touched, project_root=self._project_root)
        except Exception:
            logger.debug("Git-aware staging failed (non-blocking)", exc_info=True)
            return ""
        if not staging.staged:
            return ""
        return (
            "Git-aware staging: staged "
            f"{', '.join(staging.files)}.\n"
            f"Proposed commit message: {staging.proposed_commit_message}"
        )

    async def _verify_successful_edit(self, tc: ToolCall) -> str:
        """Run post-edit verification for files touched by one mutating tool."""
        if not self._project_root:
            return ""
        config = self._verify_config or AutoVerifyConfig()
        if not config.enabled:
            return ""
        touched = self._extract_touched_files(tc.name, tc.arguments)
        if not touched:
            return ""
        try:
            result = await verify_after_edit(
                touched,
                project_root=self._project_root,
                config=config,
            )
        except Exception as exc:
            logger.debug("Post-edit verification failed (non-blocking)", exc_info=True)
            return f"Verification unavailable: {type(exc).__name__}: {exc}"
        if not result.checked_files:
            return ""
        if result.ok:
            self._verification_failure_count = 0
            return result.to_system_message(project_root=self._project_root)

        self._verification_failure_count += 1
        note = result.to_system_message(project_root=self._project_root)
        cost_warning = self._pop_cost_limit_warning()
        if cost_warning is not None:
            total, limit = cost_warning
            return (
                f"{note}\n"
                "Verification retry halted: cost limit reached "
                f"(${total:.2f} used, ${limit:.2f} limit)."
            )
        if self._verification_failure_count >= config.max_iterations:
            plural = "s" if config.max_iterations != 1 else ""
            return (
                f"{note}\n"
                f"Verification failed after {config.max_iterations} iteration{plural}. "
                "No automatic rollback was performed. Use /rollback to inspect or restore "
                "a user-confirmed checkpoint."
            )
        return note

    def _pop_cost_limit_warning(self) -> tuple[float, float] | None:
        if self._token_tracker is None:
            return None
        pop_warning = getattr(self._token_tracker, "pop_cost_limit_warning", None)
        if not callable(pop_warning):
            return None
        warning = pop_warning()
        if warning is None:
            return None
        try:
            total, limit = warning
            return float(total), float(limit)
        except Exception:
            return None
