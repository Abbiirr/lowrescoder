"""Deterministic middleware/hooks around the agent loop.

Based on patterns from:
- Open-SWE: ToolErrorMiddleware, check_message_queue_before_model, ensure_no_empty_msg
- Claude Code: hooks before/after compaction, permission automation
- Codex: guardian review routing

Middleware runs at well-defined points in the agent loop:
- before_model: before each LLM call
- after_model: after LLM response, before tool execution
- before_tool: before each tool call
- after_tool: after tool result
- before_compaction: before context compaction
- after_compaction: after compaction completes
- on_error: when a tool or LLM call fails
- on_iteration: at the start of each loop iteration
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_PLANNING_TOOL_NAMES = frozenset({
    "create_task",
    "update_task",
    "list_tasks",
    "add_task_dependency",
})
_VERIFYING_TOOL_NAMES = frozenset({
    "run_command",
    "list_tasks",
    "read_file",
    "search_text",
    "search_code",
})
_MUTATING_TOOL_NAMES = frozenset({
    "write_file",
    "edit_file",
})
_MULTI_STEP_PATTERNS = (
    r"\b(and|then|after|before|while|across|multiple|multi-file|split|rename|refactor|"
    r"implement|migrate|wire|integrate|update.*tests|fix.*tests)\b"
)
_MAX_TOOL_RESULT_CHARS = 12_000


def looks_multi_step_request(text: str) -> bool:
    """Heuristic for tasks that should be decomposed before execution."""
    normalized = text.strip().lower()
    if not normalized:
        return False
    if len(normalized) > 120:
        return True
    if "\n-" in normalized or "\n1." in normalized:
        return True
    return re.search(_MULTI_STEP_PATTERNS, normalized) is not None


@dataclass
class MiddlewareContext:
    """Context passed to middleware functions."""

    iteration: int = 0
    tool_name: str = ""
    tool_args: dict[str, Any] = field(default_factory=dict)
    tool_result: str = ""
    messages: list[dict[str, Any]] = field(default_factory=list)
    response: Any | None = None
    error: Exception | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Control flow
    skip: bool = False  # Set True to skip the current operation
    modified_result: str | None = None  # Override tool result


# Middleware function type
MiddlewareFn = Callable[[MiddlewareContext], None]


class MiddlewareStack:
    """Ordered stack of middleware hooks.

    Middleware runs in registration order. Each middleware can:
    - Inspect and log (observability)
    - Modify context (transformation)
    - Set skip=True to cancel the operation (guard)
    - Set modified_result to override output (interception)

    The stack holds persistent shared_state across all calls,
    so middleware like repetition_detector can accumulate history.
    """

    def __init__(self) -> None:
        self._hooks: dict[str, list[MiddlewareFn]] = {
            "before_model": [],
            "after_model": [],
            "before_tool": [],
            "after_tool": [],
            "before_compaction": [],
            "after_compaction": [],
            "on_error": [],
            "on_iteration": [],
        }
        # Persistent state shared across all middleware calls
        self.shared_state: dict[str, Any] = {}

    def add(self, event: str, fn: MiddlewareFn) -> None:
        """Register a middleware function for an event."""
        if event not in self._hooks:
            raise ValueError(f"Unknown event: {event}. Valid: {list(self._hooks)}")
        self._hooks[event].append(fn)

    def run(self, event: str, ctx: MiddlewareContext) -> MiddlewareContext:
        """Run all middleware for an event. Returns (possibly modified) context.

        Injects shared_state into ctx.metadata so middleware can persist
        state across calls (e.g. repetition history).
        """
        # Inject persistent shared state
        ctx.metadata.update(self.shared_state)

        for fn in self._hooks.get(event, []):
            try:
                fn(ctx)
                if ctx.skip:
                    logger.debug("Middleware skipped %s at %s", event, fn.__name__)
                    break
            except Exception as e:
                logger.warning("Middleware %s failed: %s", fn.__name__, e)

        # Persist state back
        for key in list(ctx.metadata):
            if key.startswith("_"):
                self.shared_state[key] = ctx.metadata[key]

        return ctx

    @property
    def hook_counts(self) -> dict[str, int]:
        """Number of registered hooks per event."""
        return {k: len(v) for k, v in self._hooks.items()}


# --- Built-in middleware ---


def empty_message_guard(ctx: MiddlewareContext) -> None:
    """Guard: skip model call if messages list is empty.

    Prevents wasted LLM calls on empty context.
    Pattern from Open-SWE: ensure_no_empty_msg.
    """
    if not ctx.messages:
        ctx.skip = True
        ctx.metadata["skip_reason"] = "empty_messages"


def tool_error_handler(ctx: MiddlewareContext) -> None:
    """After-tool: format tool errors consistently.

    Pattern from Open-SWE: ToolErrorMiddleware.
    """
    if ctx.error:
        error_msg = f"Tool '{ctx.tool_name}' failed: {ctx.error}"
        ctx.modified_result = error_msg
        logger.warning(error_msg)


def iteration_logger(ctx: MiddlewareContext) -> None:
    """On-iteration: log iteration count for observability."""
    logger.debug("Agent loop iteration %d", ctx.iteration)


def repetition_detector(ctx: MiddlewareContext) -> None:
    """After-tool: detect if the agent is repeating the same tool call.

    Pattern from Goose: tool_inspection.rs repetition controls.
    Stores recent tool calls in metadata and warns on repeats.
    """
    key = f"{ctx.tool_name}:{sorted(ctx.tool_args.items())}"
    recent = ctx.metadata.get("_recent_calls", [])
    repeat_count = sum(1 for c in recent[-5:] if c == key)

    if repeat_count >= 3:
        ctx.modified_result = (
            f"{ctx.tool_result}\n\n"
            "WARNING: You have called this exact tool with the same "
            "arguments 3+ times. Try a different approach."
        )

    recent.append(key)
    if len(recent) > 10:
        recent = recent[-10:]
    ctx.metadata["_recent_calls"] = recent


def planning_bootstrap(ctx: MiddlewareContext) -> None:
    """before_model: flag multi-step tasks and inject a planning reminder once.

    This does not by itself block execution. The hard gate lives in
    planning_guard below.
    """
    if ctx.iteration != 0:
        return

    if ctx.metadata.get("_planning_initialized"):
        return

    has_tasks = bool(ctx.metadata.get("has_tasks"))
    has_task_tools = bool(ctx.metadata.get("has_task_tools"))
    user_message = str(ctx.metadata.get("user_message", ""))
    required = has_task_tools and not has_tasks and looks_multi_step_request(user_message)

    ctx.metadata["_planning_initialized"] = True
    ctx.metadata["_planning_required"] = required
    ctx.metadata["_planning_satisfied"] = has_tasks

    if not required or not ctx.messages:
        return

    ctx.messages.append({
        "role": "system",
        "content": (
            "This looks like a multi-step task. Before using non-planning tools, "
            "break the work into tasks with create_task, add_task_dependency when "
            "needed, and use list_tasks so the task board is explicit."
        ),
    })


def reasoning_budget(ctx: MiddlewareContext) -> None:
    """before_model: apply a high/low/high reasoning budget sandwich.

    High reasoning:
    - first iteration
    - when repeated tool failures have accumulated
    - when verification/planning pressure is still active late in the loop

    Low reasoning:
    - the middle execution band where the agent should mostly act.
    """
    iteration = ctx.iteration
    failures = ctx.metadata.get("_tool_failures", {})
    failure_count = (
        sum(int(count) for count in failures.values())
        if isinstance(failures, dict)
        else 0
    )
    verification_pending = bool(
        ctx.metadata.get("_verification_needed") and not ctx.metadata.get("_verification_satisfied")
    )
    planning_pending = bool(
        ctx.metadata.get("_planning_required") and not ctx.metadata.get("_planning_satisfied")
    )

    reasoning_enabled = True
    phase = "initial"
    if iteration == 0:
        reasoning_enabled = True
        phase = "initial"
    elif failure_count >= 2 or (iteration >= 3 and (verification_pending or planning_pending)):
        reasoning_enabled = True
        phase = "recovery"
    else:
        reasoning_enabled = False
        phase = "execution"

    ctx.metadata["_reasoning_enabled"] = reasoning_enabled
    ctx.metadata["_reasoning_budget_phase"] = phase


def environment_bootstrap(ctx: MiddlewareContext) -> None:
    """before_model: inject a one-time workspace snapshot on iteration zero."""
    if ctx.iteration != 0:
        return
    if ctx.metadata.get("_environment_bootstrap_done"):
        return

    snapshot = str(ctx.metadata.get("environment_snapshot", "")).strip()
    ctx.metadata["_environment_bootstrap_done"] = True
    if not snapshot or not ctx.messages:
        return

    ctx.messages.append({
        "role": "system",
        "content": f"## Workspace Bootstrap\n{snapshot}",
    })


def planning_guard(ctx: MiddlewareContext) -> None:
    """before_tool: block non-planning tools until a task plan exists."""
    if not ctx.metadata.get("_planning_required"):
        return
    if ctx.metadata.get("_planning_satisfied"):
        return
    if ctx.tool_name in _PLANNING_TOOL_NAMES:
        return

    ctx.skip = True
    ctx.modified_result = (
        "Blocked by planning enforcement: this request appears multi-step. "
        "Call create_task first, then optionally add_task_dependency and list_tasks "
        "before using other tools."
    )


def planning_progress_tracker(ctx: MiddlewareContext) -> None:
    """after_tool: mark planning as satisfied once task tools are used."""
    if ctx.tool_name not in _PLANNING_TOOL_NAMES:
        return
    if "error" in ctx.tool_result.lower():
        return
    ctx.metadata["_planning_satisfied"] = True


def verification_tracker(ctx: MiddlewareContext) -> None:
    """after_tool: track whether a mutating step still needs verification."""
    if ctx.tool_name in _MUTATING_TOOL_NAMES:
        ctx.metadata["_verification_needed"] = True
        ctx.metadata["_verification_satisfied"] = False
        ctx.metadata["_verification_prompted"] = False

        path = str(ctx.tool_args.get("path", ""))
        if path:
            edit_counts = ctx.metadata.get("_file_edit_counts", {})
            edit_counts[path] = edit_counts.get(path, 0) + 1
            ctx.metadata["_file_edit_counts"] = edit_counts
            if edit_counts[path] >= 4:
                ctx.modified_result = (
                    f"{ctx.tool_result}\n\n"
                    f"WARNING: {path} has been edited {edit_counts[path]} times in this run. "
                    "You may be in a doom loop. Verify the file state or try a different approach."
                )
        return

    if ctx.tool_name in _VERIFYING_TOOL_NAMES and ctx.metadata.get("_verification_needed"):
        ctx.metadata["_verification_satisfied"] = True


def output_hygiene(ctx: MiddlewareContext) -> None:
    """after_tool: cap oversized outputs and collapse identical repeated payloads."""
    current_result = ctx.modified_result or ctx.tool_result
    if not current_result:
        return

    repeated = ctx.metadata.get("_recent_tool_results", {})
    repeated_key = f"{ctx.tool_name}:{hash(current_result)}"
    repeated[repeated_key] = repeated.get(repeated_key, 0) + 1
    ctx.metadata["_recent_tool_results"] = repeated

    if repeated[repeated_key] >= 2:
        ctx.modified_result = (
            f"[repeated {ctx.tool_name} output collapsed; identical payload seen "
            f"{repeated[repeated_key]} times, {len(current_result)} chars]"
        )
        return

    if len(current_result) <= _MAX_TOOL_RESULT_CHARS:
        return

    head_chars = 8_000
    tail_chars = 3_000
    omitted = len(current_result) - (head_chars + tail_chars)
    ctx.modified_result = (
        current_result[:head_chars]
        + f"\n[... truncated {omitted} chars of tool output ...]\n"
        + current_result[-tail_chars:]
    )


def pre_completion_verifier(ctx: MiddlewareContext) -> None:
    """after_model: require a verification step before accepting completion.

    If the model tries to finish with plain text after file mutations but before
    any verification-style tool use, inject a one-time retry instruction.
    """
    response = ctx.response
    if response is None or getattr(response, "tool_calls", None):
        return
    if not (getattr(response, "content", "") or "").strip():
        return
    if not ctx.metadata.get("_verification_needed"):
        return
    if ctx.metadata.get("_verification_satisfied"):
        return
    if ctx.metadata.get("_verification_prompted"):
        return

    ctx.metadata["_verification_prompted"] = True
    ctx.metadata["_force_retry_user_message"] = (
        "Before declaring completion, verify your changes with tools. "
        "Run an appropriate check now (for example tests via run_command, "
        "inspect the changed file, or list_tasks if the task board changed). "
        "Do not finish yet."
    )


def tool_failure_detector(ctx: MiddlewareContext) -> None:
    """on_error: warn when the same tool keeps failing in one run."""
    failures = ctx.metadata.get("_tool_failures", {})
    failures[ctx.tool_name] = failures.get(ctx.tool_name, 0) + 1
    ctx.metadata["_tool_failures"] = failures
    if failures[ctx.tool_name] >= 3:
        ctx.modified_result = (
            f"Tool '{ctx.tool_name}' failed repeatedly ({failures[ctx.tool_name]} times). "
            "You may be in a doom loop. Reconsider the approach or gather more context."
        )


def dangerous_command_guard(ctx: MiddlewareContext) -> None:
    """Before-tool: block dangerous shell commands.

    Guards against rm -rf /, format, shutdown, etc.
    """
    if ctx.tool_name != "run_command":
        return

    cmd = ctx.tool_args.get("command", "")
    dangerous_patterns = [
        "rm -rf /",
        "rm -rf /*",
        "mkfs",
        "dd if=",
        ":(){:|:&};:",  # fork bomb
        "shutdown",
        "reboot",
        "init 0",
        "halt",
    ]
    for pattern in dangerous_patterns:
        if pattern in cmd:
            ctx.skip = True
            ctx.modified_result = f"BLOCKED: dangerous command detected ({pattern})"
            logger.warning("Blocked dangerous command: %s", cmd[:100])
            return


def artifact_logger(ctx: MiddlewareContext) -> None:
    """Log tool calls to ArtifactCollector (after_tool).

    Collects commands.log data for evidence capture. Only active
    when an ArtifactCollector is present in shared_state.
    """
    collector = ctx.metadata.get("_artifact_collector")
    if collector is None:
        return
    tool = ctx.tool_name
    args = ctx.tool_args
    result = ctx.tool_result or ""

    # Extract command string for shell tools
    if tool == "run_command":
        cmd = args.get("command", str(args))
    elif tool in ("write_file", "edit_file"):
        path = args.get("file_path", args.get("path", "?"))
        cmd = f"{tool} {path}"
        collector.log_file_change(path)
    elif tool == "read_file":
        cmd = f"read_file {args.get('file_path', args.get('path', '?'))}"
    else:
        cmd = f"{tool}({str(args)[:80]})"

    # Infer exit code from result
    exit_code = 0
    if "error" in result.lower()[:50] or "FAIL" in result[:50]:
        exit_code = 1

    duration_ms = int(ctx.metadata.get("_tool_duration_ms", 0))
    collector.log_command(cmd, exit_code=exit_code, duration_ms=duration_ms, tool_name=tool)


def auto_checkpoint(ctx: MiddlewareContext) -> None:
    """Auto-checkpoint before mutating tool calls (before_tool).

    Creates a checkpoint before write_file/edit_file/run_command
    with debouncing (skip if <30s since last checkpoint).
    """
    import time

    if ctx.tool_name not in _MUTATING_TOOL_NAMES and ctx.tool_name != "run_command":
        return

    checkpoint_store = ctx.metadata.get("_checkpoint_store")
    if checkpoint_store is None:
        return

    last_cp = ctx.metadata.get("_last_checkpoint_time", 0)
    now = time.time()
    if now - last_cp < 30:
        return  # Debounce

    try:
        checkpoint_store.save(label=f"auto-before-{ctx.tool_name}")
        ctx.metadata["_last_checkpoint_time"] = now
        logger.debug("Auto-checkpoint saved before %s", ctx.tool_name)
    except Exception as e:
        logger.debug("Auto-checkpoint failed: %s", e)


def create_default_middleware() -> MiddlewareStack:
    """Create middleware stack with sensible defaults."""
    stack = MiddlewareStack()
    stack.add("before_model", empty_message_guard)
    stack.add("before_model", environment_bootstrap)
    stack.add("before_model", planning_bootstrap)
    stack.add("before_model", reasoning_budget)
    stack.add("after_model", pre_completion_verifier)
    stack.add("before_tool", planning_guard)
    stack.add("before_tool", dangerous_command_guard)
    stack.add("before_tool", auto_checkpoint)
    stack.add("after_tool", planning_progress_tracker)
    stack.add("after_tool", verification_tracker)
    stack.add("after_tool", output_hygiene)
    stack.add("after_tool", artifact_logger)
    stack.add("after_tool", repetition_detector)
    stack.add("on_error", tool_error_handler)
    stack.add("on_error", tool_failure_detector)
    stack.add("on_iteration", iteration_logger)
    return stack
