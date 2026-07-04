from __future__ import annotations

import pytest

from autocode.agent.pev import (
    AsyncPEVRunner,
    LLMVerifier,
    PEVActivationPolicy,
    PEVRunner,
    Plan,
    PlanStep,
    Verdict,
    Verification,
)
from autocode.agent.prompts import VERIFIER_PROMPT
from autocode.layer4.llm import LLMResponse


class _ToolCall:
    def __init__(self, name: str, arguments: dict[str, object]) -> None:
        self.name = name
        self.arguments = arguments


def test_pev_runner_executes_four_step_plan_end_to_end() -> None:
    executed: list[str] = []

    def executor(step: PlanStep, feedback: str | None) -> dict[str, str]:
        executed.append(step.id)
        return {"step_id": step.id, "feedback": feedback or ""}

    def verifier(step: PlanStep, execution: object) -> Verification:
        return Verification.pass_(evidence=f"{step.id} passed")

    plan = Plan(
        goal="Refactor backend safely",
        steps=[
            PlanStep(id="inspect", description="Inspect current backend"),
            PlanStep(id="edit", description="Edit implementation"),
            PlanStep(id="test", description="Run tests"),
            PlanStep(id="docs", description="Update docs"),
        ],
        overall_success_criteria=["all steps verified"],
    )

    result = PEVRunner(executor=executor, verifier=verifier).execute_plan(plan)

    assert result.status == "succeeded"
    assert executed == ["inspect", "edit", "test", "docs"]
    assert [step_result.success for step_result in result.results] == [True] * 4
    assert result.evidence == [
        "inspect passed",
        "edit passed",
        "test passed",
        "docs passed",
    ]


def test_pev_runner_retries_step_once_with_verifier_feedback() -> None:
    attempts: list[tuple[str, str | None]] = []

    def executor(step: PlanStep, feedback: str | None) -> dict[str, object]:
        attempts.append((step.id, feedback))
        return {"attempt": len(attempts)}

    def verifier(step: PlanStep, execution: object) -> Verification:
        if len(attempts) == 1:
            return Verification.fail(
                evidence="test failed",
                next_action="retry_step",
                feedback="fix missing assertion",
            )
        return Verification.pass_(evidence="test passed after retry")

    plan = Plan(
        goal="Fix failing test",
        steps=[PlanStep(id="test", description="Run and fix test")],
    )

    result = PEVRunner(executor=executor, verifier=verifier).execute_plan(plan)

    assert result.status == "succeeded"
    assert attempts == [("test", None), ("test", "fix missing assertion")]
    assert result.results[0].attempts == 2
    assert result.results[0].success is True


@pytest.mark.asyncio
async def test_async_pev_runner_executes_awaitable_steps_with_feedback() -> None:
    attempts: list[tuple[str, str | None]] = []

    async def executor(step: PlanStep, feedback: str | None) -> dict[str, object]:
        attempts.append((step.id, feedback))
        return {"attempt": len(attempts)}

    async def verifier(step: PlanStep, execution: object) -> Verification:
        if len(attempts) == 1:
            return Verification.fail(
                evidence="manual step needs revision",
                next_action="retry_step",
                feedback="tighten the implementation",
            )
        return Verification.pass_(evidence="manual step accepted")

    plan = Plan(
        goal="Manual plan goal",
        steps=[PlanStep(id="execute", description="Execute requested work")],
    )

    result = await AsyncPEVRunner(executor=executor, verifier=verifier).execute_plan(plan)

    assert result.status == "succeeded"
    assert attempts == [
        ("execute", None),
        ("execute", "tighten the implementation"),
    ]
    assert result.results[0].attempts == 2


def test_pev_runner_surfaces_rollback_without_auto_rollback_on_abort() -> None:
    events: list[tuple[str, dict[str, object]]] = []
    rollback_requests: list[str] = []

    def executor(step: PlanStep, feedback: str | None) -> dict[str, str]:
        return {"step_id": step.id}

    def verifier(step: PlanStep, execution: object) -> Verification:
        return Verification.fail(evidence="unsafe edit", next_action="abort_plan")

    def rollback_handler(plan: Plan, step: PlanStep) -> str:
        rollback_requests.append(step.id)
        return f"Surface /rollback for {step.id}; do not auto-rollback"

    plan = Plan(
        goal="Risky refactor",
        steps=[PlanStep(id="edit", description="Edit risky file")],
        rollback_strategy="checkpoint",
    )

    result = PEVRunner(
        executor=executor,
        verifier=verifier,
        rollback_handler=rollback_handler,
        telemetry_emit=lambda kind, data: events.append((kind, data)),
    ).execute_plan(plan)

    assert result.status == "failed"
    assert rollback_requests == ["edit"]
    assert result.results[0].success is False
    assert result.results[0].next_action == "abort_plan"
    assert result.evidence[-1] == "Surface /rollback for edit; do not auto-rollback"
    assert events == [
        (
            "pev_step_failed",
            {
                "plan_step_id": "edit",
                "verdict": "fail",
                "next_action": "abort_plan",
                "attempts": 1,
            },
        )
    ]


def test_verifier_prompt_requires_valid_json_and_read_only_behavior() -> None:
    assert "Your output MUST be valid JSON" in VERIFIER_PROMPT
    assert "Do NOT modify anything" in VERIFIER_PROMPT
    assert "{step_id}" in VERIFIER_PROMPT
    assert '"verdict": "pass" | "fail" | "uncertain"' in VERIFIER_PROMPT


def test_pev_activation_policy_detects_large_todo_write_plan() -> None:
    policy = PEVActivationPolicy(min_todo_items=4)

    assert policy.should_wrap_tool_call(
        "todo_write",
        {
            "todos": [
                {"id": "1", "text": "inspect", "status": "pending"},
                {"id": "2", "text": "edit", "status": "pending"},
                {"id": "3", "text": "test", "status": "pending"},
                {"id": "4", "text": "docs", "status": "pending"},
            ]
        },
    ) is True
    assert policy.should_wrap_tool_call(
        "todo_write",
        {"todos": [{"id": "1"}, {"id": "2"}, {"id": "3"}]},
    ) is False
    assert policy.should_wrap_tool_call("read_file", {"todos": [{"id": "1"}]}) is False


def test_pev_activation_policy_builds_plan_from_todo_write() -> None:
    policy = PEVActivationPolicy(min_todo_items=4)

    plan = policy.plan_from_todo_write(
        {
            "todos": [
                {"id": "inspect", "text": "Inspect the backend", "status": "pending"},
                {"id": "edit", "text": "Edit implementation", "status": "pending"},
                {"id": "test", "text": "Run tests", "status": "pending"},
                {"id": "docs", "text": "Update docs", "status": "pending"},
            ]
        },
        goal="Large todo plan",
    )

    assert plan is not None
    assert plan.goal == "Large todo plan"
    assert [step.id for step in plan.steps] == ["inspect", "edit", "test", "docs"]
    assert plan.steps[0].description == "Inspect the backend"
    assert plan.overall_success_criteria == ["all todo steps verified"]


def test_pev_activation_policy_honors_disable_env(monkeypatch) -> None:
    monkeypatch.setenv("AUTOCODE_DISABLE_PEV", "true")
    policy = PEVActivationPolicy(min_todo_items=4)

    assert policy.is_disabled() is True
    assert policy.should_wrap_tool_call(
        "todo_write",
        {"todos": [{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}]},
    ) is False


def test_pev_hook_observes_large_todo_write_without_mutating_result() -> None:
    from autocode.agent.hooks import PEVPlanningHook

    hook = PEVPlanningHook(
        activation_policy=PEVActivationPolicy(min_todo_items=4),
    )

    result = hook.post_tool_call_success(
        _ToolCall(
            "todo_write",
            {
                "todos": [
                    {"id": "1"},
                    {"id": "2"},
                    {"id": "3"},
                    {"id": "4"},
                ]
            },
        ),
        "todo saved",
    )

    # Observer-only: the hook records activation but must NOT mutate the tool
    # result or emit telemetry — AgentLoop is the single source of truth for the
    # ``pev_activated`` event, so the hook cannot accept a telemetry sink.
    assert result is None
    assert hook.activated is True
    assert hook.activation_reason == "todo_write_large_plan"
    assert hook.todo_count == 4
    assert not hasattr(hook, "_telemetry_emit")


def test_llm_verifier_parses_pass_response() -> None:
    calls: list[list[dict[str, str]]] = []

    def model(messages: list[dict[str, str]]) -> LLMResponse:
        calls.append(messages)
        return LLMResponse(
            content='{"verdict":"pass","evidence":"tests passed","next_action":"proceed"}'
        )

    verifier = LLMVerifier(model_generate=model)
    result = verifier(
        PlanStep(id="test", description="Run tests"),
        {"stdout": "2 passed"},
    )

    assert result == Verification.pass_(evidence="tests passed")
    assert calls[0][0]["role"] == "system"
    assert "Do NOT modify anything" in calls[0][0]["content"]
    assert "Run tests" in calls[0][1]["content"]


def test_llm_verifier_parses_fail_retry_abort_and_uncertain() -> None:
    responses = iter([
        '{"verdict":"fail","evidence":"missing assertion","next_action":"retry_step",'
        '"feedback":"add assertion"}',
        '{"verdict":"fail","evidence":"unsafe edit","next_action":"abort_plan"}',
        '{"verdict":"uncertain","evidence":"needs human decision","next_action":"ask_user"}',
    ])
    verifier = LLMVerifier(model_generate=lambda _messages: next(responses))
    step = PlanStep(id="edit", description="Edit file")

    retry = verifier(step, {"stdout": "failed"})
    abort = verifier(step, {"stdout": "unsafe"})
    uncertain = verifier(step, {"stdout": "ambiguous"})

    assert retry == Verification.fail(
        evidence="missing assertion",
        next_action="retry_step",
        feedback="add assertion",
    )
    assert abort == Verification.fail(evidence="unsafe edit", next_action="abort_plan")
    assert uncertain.verdict == Verdict.UNCERTAIN
    assert uncertain.next_action == "ask_user"
    assert uncertain.evidence == "needs human decision"


def test_llm_verifier_maps_rollback_to_abort_without_auto_rollback() -> None:
    verifier = LLMVerifier(
        model_generate=lambda _messages: (
            '{"verdict":"fail","evidence":"rollback needed","next_action":"rollback"}'
        )
    )

    result = verifier(PlanStep(id="edit", description="Edit file"), {"stdout": "bad"})

    assert result == Verification.fail(
        evidence="rollback needed",
        next_action="abort_plan",
    )


def test_llm_verifier_malformed_response_returns_uncertain() -> None:
    verifier = LLMVerifier(model_generate=lambda _messages: "not json")

    result = verifier(PlanStep(id="inspect", description="Inspect"), object())

    assert result.verdict == Verdict.UNCERTAIN
    assert result.next_action == "ask_user"
    assert "invalid verifier response" in result.evidence
