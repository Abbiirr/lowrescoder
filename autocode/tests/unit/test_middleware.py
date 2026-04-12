"""Tests for deterministic middleware/hooks."""

from __future__ import annotations

from autocode.agent.middleware import (
    MiddlewareContext,
    MiddlewareStack,
    create_default_middleware,
    dangerous_command_guard,
    empty_message_guard,
    environment_bootstrap,
    looks_multi_step_request,
    output_hygiene,
    planning_guard,
    planning_progress_tracker,
    pre_completion_verifier,
    reasoning_budget,
    repetition_detector,
    tool_error_handler,
    tool_failure_detector,
    verification_tracker,
)
from autocode.layer4.llm import LLMResponse


def test_empty_message_guard() -> None:
    """Skip model call on empty messages."""
    ctx = MiddlewareContext(messages=[])
    empty_message_guard(ctx)
    assert ctx.skip


def test_empty_message_guard_passes() -> None:
    """Don't skip when messages exist."""
    ctx = MiddlewareContext(messages=[{"role": "user", "content": "hi"}])
    empty_message_guard(ctx)
    assert not ctx.skip


def test_dangerous_command_guard_blocks() -> None:
    """Block dangerous shell commands."""
    ctx = MiddlewareContext(
        tool_name="run_command",
        tool_args={"command": "rm -rf /"},
    )
    dangerous_command_guard(ctx)
    assert ctx.skip
    assert "BLOCKED" in ctx.modified_result


def test_dangerous_command_guard_allows() -> None:
    """Allow safe commands."""
    ctx = MiddlewareContext(
        tool_name="run_command",
        tool_args={"command": "ls -la"},
    )
    dangerous_command_guard(ctx)
    assert not ctx.skip


def test_dangerous_command_guard_ignores_non_shell() -> None:
    """Don't check non-shell tools."""
    ctx = MiddlewareContext(
        tool_name="read_file",
        tool_args={"path": "rm -rf /"},
    )
    dangerous_command_guard(ctx)
    assert not ctx.skip


def test_tool_error_handler() -> None:
    """Format tool errors consistently."""
    ctx = MiddlewareContext(
        tool_name="write_file",
        error=RuntimeError("disk full"),
    )
    tool_error_handler(ctx)
    assert "write_file" in ctx.modified_result
    assert "disk full" in ctx.modified_result


def test_repetition_detector() -> None:
    """Warn on repeated identical tool calls."""
    ctx = MiddlewareContext(
        tool_name="read_file",
        tool_args={"path": "same.py"},
        tool_result="content",
        metadata={"_recent_calls": []},
    )
    # Call 4 times with same args
    for _ in range(4):
        ctx.modified_result = None
        repetition_detector(ctx)

    assert ctx.modified_result is not None
    assert "different approach" in ctx.modified_result


def test_looks_multi_step_request_detects_complex_requests() -> None:
    """Long, multi-step asks should trigger planning heuristics."""
    assert looks_multi_step_request("Rename the module, update tests, and wire the CLI entrypoint")
    assert looks_multi_step_request("Implement this across multiple files")


def test_looks_multi_step_request_ignores_simple_requests() -> None:
    """Small single-step asks should not trigger planning heuristics."""
    assert not looks_multi_step_request("Read app.py")
    assert not looks_multi_step_request("")


def test_planning_guard_blocks_non_planning_tools() -> None:
    """Multi-step execution should require task creation before other tools."""
    ctx = MiddlewareContext(
        tool_name="read_file",
        metadata={"_planning_required": True, "_planning_satisfied": False},
    )
    planning_guard(ctx)
    assert ctx.skip
    assert "create_task" in (ctx.modified_result or "")


def test_planning_progress_tracker_marks_plan_satisfied() -> None:
    """Successful task-tool use should unlock execution."""
    ctx = MiddlewareContext(
        tool_name="create_task",
        tool_result="Created task 'Investigate bug' (id: abc12345)",
        metadata={"_planning_satisfied": False},
    )
    planning_progress_tracker(ctx)
    assert ctx.metadata["_planning_satisfied"] is True


def test_verification_tracker_warns_on_repeated_edits() -> None:
    """Repeated edits to the same file should surface a doom-loop warning."""
    ctx = MiddlewareContext(
        tool_name="edit_file",
        tool_args={"path": "src/app.py"},
        tool_result="edit applied",
        metadata={},
    )

    for _ in range(4):
        ctx.modified_result = None
        verification_tracker(ctx)

    assert ctx.metadata["_verification_needed"] is True
    assert ctx.metadata["_verification_satisfied"] is False
    assert "doom loop" in (ctx.modified_result or "").lower()


def test_pre_completion_verifier_injects_retry() -> None:
    """Plain-text completion after edits should require verification."""
    ctx = MiddlewareContext(
        response=LLMResponse(content="Done, fixed it."),
        metadata={
            "_verification_needed": True,
            "_verification_satisfied": False,
            "_verification_prompted": False,
        },
    )
    pre_completion_verifier(ctx)
    assert "verify your changes" in ctx.metadata["_force_retry_user_message"].lower()
    assert ctx.metadata["_verification_prompted"] is True


def test_tool_failure_detector_warns_after_repeated_errors() -> None:
    """Repeated tool failures should surface a doom-loop warning."""
    ctx = MiddlewareContext(tool_name="run_command", metadata={})
    for _ in range(3):
        ctx.modified_result = None
        tool_failure_detector(ctx)

    assert "doom loop" in (ctx.modified_result or "").lower()


def test_environment_bootstrap_injects_workspace_snapshot() -> None:
    """Iteration zero should inject the workspace snapshot once."""
    ctx = MiddlewareContext(
        iteration=0,
        messages=[{"role": "system", "content": "base prompt"}],
        metadata={"environment_snapshot": "- Project root: /tmp/repo"},
    )
    environment_bootstrap(ctx)
    assert ctx.metadata["_environment_bootstrap_done"] is True
    assert any(
        msg.get("role") == "system" and "Workspace Bootstrap" in msg.get("content", "")
        for msg in ctx.messages
    )


def test_reasoning_budget_uses_high_low_high_sandwich() -> None:
    """Reasoning should be high on iteration zero, low mid-loop, high again on recovery."""
    first = MiddlewareContext(iteration=0, metadata={})
    reasoning_budget(first)
    assert first.metadata["_reasoning_enabled"] is True
    assert first.metadata["_reasoning_budget_phase"] == "initial"

    middle = MiddlewareContext(iteration=1, metadata={})
    reasoning_budget(middle)
    assert middle.metadata["_reasoning_enabled"] is False
    assert middle.metadata["_reasoning_budget_phase"] == "execution"

    recovery = MiddlewareContext(
        iteration=4,
        metadata={"_verification_needed": True, "_verification_satisfied": False},
    )
    reasoning_budget(recovery)
    assert recovery.metadata["_reasoning_enabled"] is True
    assert recovery.metadata["_reasoning_budget_phase"] == "recovery"


def test_reasoning_budget_escalates_after_repeated_failures() -> None:
    """Repeated failures should push the loop back into high-reasoning mode."""
    ctx = MiddlewareContext(
        iteration=2,
        metadata={"_tool_failures": {"run_command": 2}},
    )
    reasoning_budget(ctx)
    assert ctx.metadata["_reasoning_enabled"] is True
    assert ctx.metadata["_reasoning_budget_phase"] == "recovery"


def test_output_hygiene_truncates_oversized_payloads() -> None:
    """Large tool outputs should be truncated with an explicit marker."""
    ctx = MiddlewareContext(
        tool_name="run_command",
        tool_result="x" * 15_000,
        metadata={},
    )
    output_hygiene(ctx)
    assert ctx.modified_result is not None
    assert "truncated" in ctx.modified_result
    assert len(ctx.modified_result) < len(ctx.tool_result)


def test_output_hygiene_collapses_identical_repeated_payloads() -> None:
    """Repeated identical tool payloads should collapse to a short marker."""
    ctx = MiddlewareContext(
        tool_name="run_command",
        tool_result="same output",
        metadata={},
    )
    output_hygiene(ctx)
    assert ctx.modified_result is None

    output_hygiene(ctx)
    assert "collapsed" in (ctx.modified_result or "")


def test_middleware_stack_ordering() -> None:
    """Middleware runs in registration order."""
    order: list[str] = []
    stack = MiddlewareStack()
    stack.add("before_tool", lambda ctx: order.append("first"))
    stack.add("before_tool", lambda ctx: order.append("second"))

    stack.run("before_tool", MiddlewareContext())
    assert order == ["first", "second"]


def test_middleware_skip_stops_chain() -> None:
    """Setting skip=True stops the middleware chain."""
    calls: list[str] = []
    stack = MiddlewareStack()

    def blocker(ctx: MiddlewareContext) -> None:
        ctx.skip = True
        calls.append("blocker")

    def after(ctx: MiddlewareContext) -> None:
        calls.append("after")

    stack.add("before_tool", blocker)
    stack.add("before_tool", after)

    stack.run("before_tool", MiddlewareContext())
    assert calls == ["blocker"]  # "after" never ran


def test_default_middleware() -> None:
    """Default middleware has expected hooks."""
    stack = create_default_middleware()
    counts = stack.hook_counts
    assert counts["before_model"] >= 1
    assert counts["before_tool"] >= 1
    assert counts["after_tool"] >= 1
    assert counts["on_iteration"] >= 1
