"""Subagent orchestration: LLM scheduler, subagent loop, and manager.

Sprint 4B: Isolated subagent execution with LLM scheduler queue,
capability-based tool restrictions, and lifecycle management.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from autocode.agent.delegation import DelegationPolicy
from autocode.agent.tools import ToolRegistry
from autocode.layer4.llm import LLMResponse, ToolCall

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LLM Scheduler — single-worker priority queue
# ---------------------------------------------------------------------------


class LLMScheduler:
    """Single-worker queue that serializes all LLM calls with foreground priority.

    Design: one asyncio.Task drains a PriorityQueue. Foreground requests
    (priority=0) always run before background requests (priority=1).
    """

    def __init__(self) -> None:
        self._queue: asyncio.PriorityQueue[
            tuple[int, int, Any, asyncio.Future[Any]]
        ] = asyncio.PriorityQueue()
        self._worker_task: asyncio.Task[None] | None = None
        self._counter: int = 0  # Tie-breaker for equal priority (FIFO within tier)
        self._active: bool = False

    def start(self) -> None:
        """Start the single-worker drain loop."""
        if self._worker_task is None or self._worker_task.done():
            self._active = True
            self._worker_task = asyncio.create_task(self._worker())

    async def submit(self, coro: Any, *, foreground: bool = True) -> Any:
        """Submit an LLM call coroutine. Returns the result when complete."""
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        priority = 0 if foreground else 1
        self._counter += 1
        await self._queue.put((priority, self._counter, coro, future))
        return await future

    @property
    def queue_depth(self) -> int:
        """Number of items waiting in the queue."""
        return self._queue.qsize()

    @property
    def is_running(self) -> bool:
        """Whether the scheduler worker is active."""
        return self._worker_task is not None and not self._worker_task.done()

    async def _worker(self) -> None:
        """Single worker drains the queue sequentially."""
        while self._active:
            try:
                priority, _, coro, future = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0,
                )
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                result = await coro
                if not future.done():
                    future.set_result(result)
            except asyncio.CancelledError:
                if not future.done():
                    future.cancel()
            except Exception as e:
                if not future.done():
                    future.set_exception(e)
            finally:
                self._queue.task_done()

    async def shutdown(self) -> None:
        """Stop the worker and cancel pending items."""
        self._active = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None


# ---------------------------------------------------------------------------
# Subagent types and result
# ---------------------------------------------------------------------------


class SubagentType(StrEnum):
    EXPLORE = "explore"
    PLAN = "plan"
    EXECUTE = "execute"


@dataclass
class SubagentResult:
    """Structured result from a completed subagent run."""

    subagent_id: str
    subagent_type: str
    task: str
    summary: str
    files_touched: list[str] = field(default_factory=list)
    status: str = "completed"  # completed, failed, cancelled
    iterations_used: int = 0
    duration_ms: int = 0


# ---------------------------------------------------------------------------
# SubagentLoop — restricted mini agent loop
# ---------------------------------------------------------------------------


class SubagentLoop:
    """Runs a restricted agent loop for a single subagent task.

    Key differences from AgentLoop:
    - Stateless: no session store, fresh context each invocation
    - Restricted tools: filtered by subagent type via capability flags
    - Background LLM priority via LLMScheduler
    - Circuit breaker: 2 consecutive errors = auto-cancel
    - Cannot spawn sub-subagents (flat hierarchy)
    """

    def __init__(
        self,
        provider: Any,
        tool_registry: ToolRegistry,
        scheduler: LLMScheduler,
        subagent_type: SubagentType,
        *,
        max_iterations: int = 5,
        timeout_seconds: int = 30,
    ) -> None:
        self._provider = provider
        self._full_registry = tool_registry
        self._scheduler = scheduler
        self._type = subagent_type
        self._max_iterations = max_iterations
        self._timeout = timeout_seconds
        self._cancelled = False
        self._files_touched: list[str] = []

        # Build restricted tool registry based on subagent type
        self._tools = self._build_restricted_registry()

    def _build_restricted_registry(self) -> ToolRegistry:
        """Build a tool registry filtered by subagent type capabilities."""
        restricted = ToolRegistry()
        for tool in self._full_registry.get_all():
            # Never allow sub-subagent spawning
            if tool.name in ("spawn_subagent", "check_subagent",
                             "cancel_subagent", "list_subagents"):
                continue

            if self._type == SubagentType.EXPLORE:
                # Read-only: no fs mutation, no shell
                if tool.mutates_fs or tool.executes_shell:
                    continue
            elif self._type == SubagentType.PLAN:
                # Read-only + task tools
                if tool.mutates_fs or tool.executes_shell:
                    # Allow task tools even though they don't have these flags
                    continue
            # SubagentType.EXECUTE gets all tools (minus subagent tools)

            restricted.register(tool)
        return restricted

    def cancel(self) -> None:
        """Cancel this subagent."""
        self._cancelled = True

    async def run(self, task: str, context: str = "") -> SubagentResult:
        """Run the subagent loop for a task description.

        Args:
            task: Description of what to do.
            context: Optional additional context.

        Returns:
            SubagentResult with summary and metadata.
        """
        start_time = time.monotonic()
        self._cancelled = False
        self._files_touched = []

        subagent_id = uuid.uuid4().hex[:8]
        tool_schemas = self._tools.get_schemas_openai_format()

        # Build initial messages
        system_prompt = (
            f"You are a {self._type.value} subagent. "
            f"Complete this task concisely:\n{task}"
        )
        if context:
            system_prompt += f"\n\nContext:\n{context}"

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task},
        ]

        consecutive_errors = 0
        last_text = ""

        try:
            result = await asyncio.wait_for(
                self._run_loop(
                    subagent_id, messages, tool_schemas,
                    consecutive_errors, last_text,
                ),
                timeout=self._timeout,
            )
            return result
        except TimeoutError:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.warning("Subagent %s timed out after %dms", subagent_id, duration_ms)
            return SubagentResult(
                subagent_id=subagent_id,
                subagent_type=self._type.value,
                task=task,
                summary=last_text or "[Timed out]",
                files_touched=self._files_touched,
                status="failed",
                iterations_used=0,
                duration_ms=duration_ms,
            )
        except asyncio.CancelledError:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return SubagentResult(
                subagent_id=subagent_id,
                subagent_type=self._type.value,
                task=task,
                summary=last_text or "[Cancelled]",
                files_touched=self._files_touched,
                status="cancelled",
                iterations_used=0,
                duration_ms=duration_ms,
            )

    async def _run_loop(
        self,
        subagent_id: str,
        messages: list[dict[str, Any]],
        tool_schemas: list[dict[str, Any]],
        consecutive_errors: int,
        last_text: str,
    ) -> SubagentResult:
        """Inner loop — separated for timeout wrapping."""
        start_time = time.monotonic()

        for iteration in range(self._max_iterations):
            if self._cancelled:
                duration_ms = int((time.monotonic() - start_time) * 1000)
                return SubagentResult(
                    subagent_id=subagent_id,
                    subagent_type=self._type.value,
                    task=messages[1]["content"],
                    summary=last_text or "[Cancelled]",
                    files_touched=self._files_touched,
                    status="cancelled",
                    iterations_used=iteration,
                    duration_ms=duration_ms,
                )

            # Submit LLM call via scheduler (background priority)
            response: LLMResponse = await self._scheduler.submit(
                self._provider.generate_with_tools(messages, tool_schemas),
                foreground=False,
            )

            # Text-only response means we're done
            if not response.tool_calls:
                last_text = response.content or ""
                duration_ms = int((time.monotonic() - start_time) * 1000)
                return SubagentResult(
                    subagent_id=subagent_id,
                    subagent_type=self._type.value,
                    task=messages[1]["content"],
                    summary=last_text,
                    files_touched=self._files_touched,
                    status="completed",
                    iterations_used=iteration + 1,
                    duration_ms=duration_ms,
                )

            if response.content:
                last_text = response.content

            # Process tool calls
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": __import__("json").dumps(tc.arguments),
                        },
                    }
                    for tc in response.tool_calls
                ],
            }
            messages.append(assistant_msg)

            for tc in response.tool_calls:
                result = self._execute_tool(tc)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

                # Track errors for circuit breaker
                if result.startswith("Error:") or result.startswith("Blocked:"):
                    consecutive_errors += 1
                else:
                    consecutive_errors = 0

                # Track files touched
                if tc.name == "write_file" and not result.startswith("Error:"):
                    path = tc.arguments.get("path", "")
                    if path and path not in self._files_touched:
                        self._files_touched.append(path)

            # Circuit breaker: 2 consecutive errors = auto-cancel
            if consecutive_errors >= 2:  # noqa: PLR2004
                duration_ms = int((time.monotonic() - start_time) * 1000)
                logger.warning(
                    "Subagent %s circuit breaker triggered after %d consecutive errors",
                    subagent_id, consecutive_errors,
                )
                return SubagentResult(
                    subagent_id=subagent_id,
                    subagent_type=self._type.value,
                    task=messages[1]["content"],
                    summary=last_text or "[Circuit breaker: consecutive errors]",
                    files_touched=self._files_touched,
                    status="failed",
                    iterations_used=iteration + 1,
                    duration_ms=duration_ms,
                )

        # Max iterations
        duration_ms = int((time.monotonic() - start_time) * 1000)
        return SubagentResult(
            subagent_id=subagent_id,
            subagent_type=self._type.value,
            task=messages[1]["content"],
            summary=last_text or "[Max iterations reached]",
            files_touched=self._files_touched,
            status="completed",
            iterations_used=self._max_iterations,
            duration_ms=duration_ms,
        )

    def _execute_tool(self, tc: ToolCall) -> str:
        """Execute a tool call with subagent restrictions.

        Background subagents auto-deny approval-requiring tools.
        """
        tool = self._tools.get(tc.name)
        if tool is None:
            return f"Error: unknown tool '{tc.name}'"

        # Auto-deny approval-requiring tools in background subagents
        if tool.requires_approval:
            return (
                f"Blocked: '{tc.name}' requires user approval. "
                "Background subagents cannot request approval."
            )

        try:
            return tool.handler(**tc.arguments)
        except Exception as e:
            return f"Error: {e}"


# ---------------------------------------------------------------------------
# SubagentManager — lifecycle management
# ---------------------------------------------------------------------------


class SubagentManager:
    """Manages subagent lifecycle: spawn, cancel, and status tracking."""

    def __init__(
        self,
        provider: Any,
        tool_registry: ToolRegistry,
        scheduler: LLMScheduler,
        *,
        max_concurrent: int = 3,
        max_iterations: int = 5,
        timeout_seconds: int = 30,
        on_state_change: Any | None = None,
        delegation_policy: DelegationPolicy | None = None,
    ) -> None:
        self._provider = provider
        self._tool_registry = tool_registry
        self._scheduler = scheduler
        self._max_concurrent = max_concurrent
        self._max_iterations = max_iterations
        self._timeout = timeout_seconds
        self._on_state_change = on_state_change
        self._delegation_policy = delegation_policy

        self._active: dict[str, asyncio.Task[SubagentResult]] = {}
        self._active_meta: dict[str, dict[str, str]] = {}
        self._loops: dict[str, SubagentLoop] = {}
        self._results: dict[str, SubagentResult] = {}

    def spawn(
        self,
        subagent_type: str,
        task: str,
        context: str = "",
    ) -> str:
        """Spawn a new subagent. Returns the subagent ID.

        Raises:
            RuntimeError: If max concurrent subagents reached.
        """
        if len(self._active) >= self._max_concurrent:
            raise RuntimeError(
                f"Max concurrent subagents ({self._max_concurrent}) reached. "
                "Cancel or wait for existing subagents."
            )

        try:
            sa_type = SubagentType(subagent_type)
        except ValueError:
            raise ValueError(  # noqa: B904
                f"Invalid subagent type '{subagent_type}'. "
                f"Valid types: {', '.join(t.value for t in SubagentType)}"
            )

        if self._delegation_policy is not None:
            role = {
                SubagentType.EXPLORE.value: "scout",
                SubagentType.PLAN.value: "architect",
                SubagentType.EXECUTE.value: "engineer",
            }.get(sa_type.value, "subagent")
            allowed, reason = self._delegation_policy.can_spawn(role)
            if not allowed:
                raise RuntimeError(f"Delegation blocked: {reason}")
            self._delegation_policy.spawn(role)

        loop = SubagentLoop(
            provider=self._provider,
            tool_registry=self._tool_registry,
            scheduler=self._scheduler,
            subagent_type=sa_type,
            max_iterations=self._max_iterations,
            timeout_seconds=self._timeout,
        )

        subagent_id = uuid.uuid4().hex[:8]
        self._loops[subagent_id] = loop

        async def _run_and_store() -> SubagentResult:
            result = await loop.run(task, context)
            result.subagent_id = subagent_id
            self._results[subagent_id] = result
            logger.info(
                "Subagent %s (%s) finished: %s (%d iterations, %dms)",
                subagent_id, subagent_type, result.status,
                result.iterations_used, result.duration_ms,
            )
            return result

        def _on_done(t: asyncio.Task[SubagentResult]) -> None:
            self._active.pop(subagent_id, None)
            self._active_meta.pop(subagent_id, None)
            self._loops.pop(subagent_id, None)
            if self._delegation_policy is not None:
                self._delegation_policy.release()
            if t.cancelled() and subagent_id not in self._results:
                self._results[subagent_id] = SubagentResult(
                    subagent_id=subagent_id,
                    subagent_type=subagent_type,
                    task=task,
                    summary="[Cancelled by manager]",
                    status="cancelled",
                )
                logger.info("Subagent %s cancelled by manager", subagent_id)
            if self._on_state_change:
                self._on_state_change()

        atask = asyncio.create_task(_run_and_store())
        atask.add_done_callback(_on_done)
        self._active[subagent_id] = atask
        self._active_meta[subagent_id] = {"type": subagent_type, "task": task[:100]}
        logger.info(
            "Spawned subagent %s (type=%s, task=%s)",
            subagent_id, subagent_type, task[:60],
        )
        if self._on_state_change:
            self._on_state_change()
        return subagent_id

    def cancel(self, subagent_id: str) -> bool:
        """Cancel a running subagent. Returns True if cancelled."""
        loop = self._loops.get(subagent_id)
        if loop:
            loop.cancel()
        task = self._active.get(subagent_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    def cancel_all(self) -> int:
        """Cancel all running subagents. Returns count cancelled."""
        count = 0
        for subagent_id in list(self._active.keys()):
            if self.cancel(subagent_id):
                count += 1
        return count

    def get_result(self, subagent_id: str) -> SubagentResult | None:
        """Get the result of a completed subagent."""
        return self._results.get(subagent_id)

    def get_status(self, subagent_id: str) -> dict[str, Any]:
        """Get current status of a subagent."""
        if subagent_id in self._active:
            meta = self._active_meta.get(subagent_id, {})
            return {
                "id": subagent_id, "status": "running",
                "type": meta.get("type", "unknown"),
                "summary": meta.get("task", ""),
            }
        result = self._results.get(subagent_id)
        if result:
            return {
                "id": subagent_id,
                "status": result.status,
                "summary": result.summary[:200],
                "iterations": result.iterations_used,
                "duration_ms": result.duration_ms,
            }
        return {"id": subagent_id, "status": "not_found"}

    def list_all(self) -> list[dict[str, Any]]:
        """List all subagents (active and completed)."""
        items: list[dict[str, Any]] = []
        for sid in self._active:
            meta = self._active_meta.get(sid, {})
            items.append({
                "id": sid, "status": "running",
                "type": meta.get("type", "unknown"),
                "summary": meta.get("task", ""),
            })
        for sid, result in self._results.items():
            if sid not in self._active:
                items.append({
                    "id": sid,
                    "status": result.status,
                    "type": result.subagent_type,
                    "summary": result.summary[:100],
                })
        return items

    def get_status_summary(self) -> str:
        """Get a compact summary for system prompt injection."""
        active = list(self._active.keys())
        if not active and not self._results:
            return ""

        lines: list[str] = []
        for sid in active:
            lines.append(f"- [{sid}] running")
        for sid, result in self._results.items():
            if sid not in self._active:
                lines.append(
                    f"- [{sid}] {result.status}: {result.summary[:80]}"
                )
        return "\n".join(lines)

    @property
    def active_count(self) -> int:
        """Number of currently running subagents."""
        return len(self._active)
