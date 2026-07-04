"""Plan-Execute-Verify core primitives."""

from __future__ import annotations

import inspect
import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal


class Verdict(StrEnum):
    """Verifier verdict values."""

    PASS = "pass"
    FAIL = "fail"
    UNCERTAIN = "uncertain"


NextAction = Literal["continue", "retry_step", "abort_plan", "ask_user"]
PlanStatus = Literal["succeeded", "failed", "user_aborted"]
RollbackStrategy = Literal["checkpoint", "revert", "abort"]


@dataclass(frozen=True, slots=True)
class PlanStep:
    """One bounded step in a PEV plan."""

    id: str
    description: str
    tools_allowed: list[str] = field(default_factory=list)
    success_predicate: str = ""
    failure_predicate: str = ""
    max_iterations: int = 1


@dataclass(frozen=True, slots=True)
class Plan:
    """A PEV plan with ordered steps and rollback policy."""

    goal: str
    steps: list[PlanStep]
    overall_success_criteria: list[str] = field(default_factory=list)
    rollback_strategy: RollbackStrategy = "checkpoint"


@dataclass(frozen=True, slots=True)
class Verification:
    """Structured verifier output for a step execution."""

    verdict: Verdict
    evidence: str
    next_action: NextAction = "continue"
    feedback: str = ""

    @classmethod
    def pass_(cls, *, evidence: str) -> Verification:
        return cls(Verdict.PASS, evidence, "continue", "")

    @classmethod
    def fail(
        cls,
        *,
        evidence: str,
        next_action: NextAction = "abort_plan",
        feedback: str = "",
    ) -> Verification:
        return cls(Verdict.FAIL, evidence, next_action, feedback)

    @classmethod
    def uncertain(cls, *, evidence: str, feedback: str = "") -> Verification:
        return cls(Verdict.UNCERTAIN, evidence, "ask_user", feedback)


@dataclass(frozen=True, slots=True)
class StepResult:
    """Result for one plan step."""

    step: PlanStep
    success: bool
    verdict: Verdict
    evidence: str
    execution: Any = None
    attempts: int = 1
    next_action: NextAction = "continue"

    @classmethod
    def success_result(
        cls,
        *,
        step: PlanStep,
        verification: Verification,
        execution: Any,
        attempts: int,
    ) -> StepResult:
        return cls(
            step=step,
            success=True,
            verdict=verification.verdict,
            evidence=verification.evidence,
            execution=execution,
            attempts=attempts,
            next_action=verification.next_action,
        )

    @classmethod
    def failure_result(
        cls,
        *,
        step: PlanStep,
        verification: Verification,
        execution: Any,
        attempts: int,
    ) -> StepResult:
        return cls(
            step=step,
            success=False,
            verdict=verification.verdict,
            evidence=verification.evidence,
            execution=execution,
            attempts=attempts,
            next_action=verification.next_action,
        )


@dataclass(frozen=True, slots=True)
class PlanResult:
    """Final PEV plan execution result."""

    plan: Plan
    results: list[StepResult]
    status: PlanStatus
    evidence: list[str]


Executor = Callable[[PlanStep, str | None], Any]
Verifier = Callable[[PlanStep, Any], Verification]
AsyncExecutor = Callable[[PlanStep, str | None], Any]
AsyncVerifier = Callable[[PlanStep, Any], Any]
RollbackHandler = Callable[[Plan, PlanStep], str]
AskUserHandler = Callable[[Plan, PlanStep, Verification], bool]
AsyncAskUserHandler = Callable[[Plan, PlanStep, Verification], Any]
TelemetryEmit = Callable[[str, dict[str, Any]], None]
ModelGenerate = Callable[[list[dict[str, str]]], Any]


@dataclass(frozen=True, slots=True)
class PEVActivationPolicy:
    """Pure activation rules for deciding when AgentLoop should enter PEV."""

    min_todo_items: int = 4
    disable_env_var: str = "AUTOCODE_DISABLE_PEV"

    def is_disabled(self) -> bool:
        return os.environ.get(self.disable_env_var, "").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def should_wrap_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        return (
            not self.is_disabled()
            and tool_name == "todo_write"
            and self.todo_count(arguments) >= self.min_todo_items
        )

    def plan_from_todo_write(self, arguments: dict[str, Any], *, goal: str) -> Plan | None:
        """Convert a large todo_write payload into deterministic PEV boundaries."""
        todos = self._todos(arguments)
        if len(todos) < self.min_todo_items:
            return None
        steps: list[PlanStep] = []
        for idx, todo in enumerate(todos, start=1):
            if not isinstance(todo, Mapping):
                continue
            raw_id = str(todo.get("id") or idx)
            text = str(todo.get("text") or todo.get("content") or raw_id).strip()
            steps.append(
                PlanStep(
                    id=_safe_step_id(raw_id, fallback=f"step-{idx}"),
                    description=text or f"Complete todo {idx}",
                    success_predicate="todo step completed and verified",
                    failure_predicate="todo step failed or regressed",
                    max_iterations=1,
                )
            )
        if len(steps) < self.min_todo_items:
            return None
        return Plan(
            goal=goal,
            steps=steps,
            overall_success_criteria=["all todo steps verified"],
            rollback_strategy="checkpoint",
        )

    @staticmethod
    def todo_count(arguments: dict[str, Any]) -> int:
        return len(PEVActivationPolicy._todos(arguments))

    @staticmethod
    def _todos(arguments: dict[str, Any]) -> list[Any]:
        todos = arguments.get("todos", [])
        if isinstance(todos, str):
            try:
                todos = json.loads(todos)
            except json.JSONDecodeError:
                return []
        if not isinstance(todos, list | tuple):
            return []
        return list(todos)


class LLMVerifier:
    """Convert model verifier JSON into PEV Verification objects."""

    def __init__(self, *, model_generate: ModelGenerate) -> None:
        self.model_generate = model_generate

    def __call__(self, step: PlanStep, execution: Any) -> Verification:
        response = self.model_generate(self._messages(step, execution))
        return self.parse_response(_response_content(response))

    @staticmethod
    def parse_response(content: str) -> Verification:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return Verification.uncertain(
                evidence="invalid verifier response: expected JSON",
                feedback=content,
            )
        if not isinstance(parsed, Mapping):
            return Verification.uncertain(
                evidence="invalid verifier response: expected JSON object",
                feedback=content,
            )

        verdict_raw = str(parsed.get("verdict", "")).strip().lower()
        evidence = str(parsed.get("evidence") or "verifier returned no evidence")
        next_action = _normalize_next_action(parsed.get("next_action"), verdict_raw)
        feedback = str(parsed.get("feedback") or "")

        if verdict_raw == "pass":
            return Verification.pass_(evidence=evidence)
        if verdict_raw == "fail":
            return Verification.fail(
                evidence=evidence,
                next_action=next_action if next_action != "ask_user" else "abort_plan",
                feedback=feedback,
            )
        if verdict_raw == "uncertain":
            return Verification.uncertain(evidence=evidence, feedback=feedback)
        return Verification.uncertain(
            evidence=f"invalid verifier response: unknown verdict {verdict_raw or '<empty>'}",
            feedback=content,
        )

    @staticmethod
    def _messages(step: PlanStep, execution: Any) -> list[dict[str, str]]:
        return build_verifier_messages(step, execution)


def build_verifier_messages(step: PlanStep, execution: Any) -> list[dict[str, str]]:
    """Build the verifier prompt messages for sync or async verifier callers."""
    from autocode.agent.prompts import VERIFIER_PROMPT

    return [
        {"role": "system", "content": VERIFIER_PROMPT},
        {
            "role": "user",
            "content": (
                f"Step ID: {step.id}\n"
                f"Step description: {step.description}\n"
                f"Success predicate: {step.success_predicate or '(none)'}\n"
                f"Failure predicate: {step.failure_predicate or '(none)'}\n"
                f"Execution result:\n{_stringify_execution(execution)}"
            ),
        },
    ]


class PEVRunner:
    """Execute plan steps and verify each boundary with retry/abort semantics."""

    def __init__(
        self,
        *,
        executor: Executor,
        verifier: Verifier,
        rollback_handler: RollbackHandler | None = None,
        ask_user_handler: AskUserHandler | None = None,
        telemetry_emit: TelemetryEmit | None = None,
    ) -> None:
        self.executor = executor
        self.verifier = verifier
        self.rollback_handler = rollback_handler or self._default_rollback_handler
        self.ask_user_handler = ask_user_handler or self._default_ask_user_handler
        self.telemetry_emit = telemetry_emit

    def execute_plan(self, plan: Plan) -> PlanResult:
        results: list[StepResult] = []
        evidence: list[str] = []

        for step in plan.steps:
            step_result = self._execute_step(plan, step, evidence)
            results.append(step_result)
            if not step_result.success:
                return PlanResult(plan, results, "failed", evidence)

        return PlanResult(plan, results, "succeeded", evidence)

    def _execute_step(
        self,
        plan: Plan,
        step: PlanStep,
        evidence: list[str],
    ) -> StepResult:
        feedback: str | None = None
        last_execution: Any = None
        attempts = 0
        max_attempts = max(step.max_iterations, 1) + 1

        while attempts < max_attempts:
            attempts += 1
            last_execution = self.executor(step, feedback)
            verification = self.verifier(step, last_execution)
            evidence.append(verification.evidence)

            if verification.verdict == Verdict.PASS:
                return StepResult.success_result(
                    step=step,
                    verification=verification,
                    execution=last_execution,
                    attempts=attempts,
                )

            if (
                verification.verdict == Verdict.FAIL
                and verification.next_action == "retry_step"
                and attempts < max_attempts
            ):
                feedback = verification.feedback or verification.evidence
                continue

            if verification.verdict == Verdict.UNCERTAIN:
                if self.ask_user_handler(plan, step, verification):
                    continue
                return StepResult.failure_result(
                    step=step,
                    verification=verification,
                    execution=last_execution,
                    attempts=attempts,
                )

            if verification.next_action == "abort_plan":
                evidence.append(self.rollback_handler(plan, step))
            self._emit_step_failure(step, verification, attempts)
            return StepResult.failure_result(
                step=step,
                verification=verification,
                execution=last_execution,
                attempts=attempts,
            )

        verification = Verification.fail(evidence="step exceeded retry budget")
        self._emit_step_failure(step, verification, attempts)
        return StepResult.failure_result(
            step=step,
            verification=verification,
            execution=last_execution,
            attempts=attempts,
        )

    def _emit_step_failure(
        self,
        step: PlanStep,
        verification: Verification,
        attempts: int,
    ) -> None:
        if self.telemetry_emit is None:
            return
        self.telemetry_emit(
            "pev_step_failed",
            {
                "plan_step_id": step.id,
                "verdict": verification.verdict.value,
                "next_action": verification.next_action,
                "attempts": attempts,
            },
        )

    @staticmethod
    def _default_rollback_handler(plan: Plan, step: PlanStep) -> str:
        return (
            f"Plan '{plan.goal}' step '{step.id}' failed. "
            f"Surface /rollback using {plan.rollback_strategy}; do not auto-rollback."
        )

    @staticmethod
    def _default_ask_user_handler(
        plan: Plan,
        step: PlanStep,
        verification: Verification,
    ) -> bool:
        return False


class AsyncPEVRunner:
    """Async PEV runner for UI/backend command paths that await agent turns."""

    def __init__(
        self,
        *,
        executor: AsyncExecutor,
        verifier: AsyncVerifier,
        rollback_handler: RollbackHandler | None = None,
        ask_user_handler: AsyncAskUserHandler | None = None,
        telemetry_emit: TelemetryEmit | None = None,
    ) -> None:
        self.executor = executor
        self.verifier = verifier
        self.rollback_handler = rollback_handler or PEVRunner._default_rollback_handler
        self.ask_user_handler = ask_user_handler or self._default_ask_user_handler
        self.telemetry_emit = telemetry_emit

    async def execute_plan(self, plan: Plan) -> PlanResult:
        results: list[StepResult] = []
        evidence: list[str] = []

        for step in plan.steps:
            step_result = await self._execute_step(plan, step, evidence)
            results.append(step_result)
            if not step_result.success:
                return PlanResult(plan, results, "failed", evidence)

        return PlanResult(plan, results, "succeeded", evidence)

    async def _execute_step(
        self,
        plan: Plan,
        step: PlanStep,
        evidence: list[str],
    ) -> StepResult:
        feedback: str | None = None
        last_execution: Any = None
        attempts = 0
        max_attempts = max(step.max_iterations, 1) + 1

        while attempts < max_attempts:
            attempts += 1
            last_execution = await _maybe_await(self.executor(step, feedback))
            verification = await _maybe_await(self.verifier(step, last_execution))
            evidence.append(verification.evidence)

            if verification.verdict == Verdict.PASS:
                return StepResult.success_result(
                    step=step,
                    verification=verification,
                    execution=last_execution,
                    attempts=attempts,
                )

            if (
                verification.verdict == Verdict.FAIL
                and verification.next_action == "retry_step"
                and attempts < max_attempts
            ):
                feedback = verification.feedback or verification.evidence
                continue

            if verification.verdict == Verdict.UNCERTAIN:
                should_retry = await _maybe_await(
                    self.ask_user_handler(plan, step, verification)
                )
                if bool(should_retry):
                    continue
                return StepResult.failure_result(
                    step=step,
                    verification=verification,
                    execution=last_execution,
                    attempts=attempts,
                )

            if verification.next_action == "abort_plan":
                evidence.append(self.rollback_handler(plan, step))
            self._emit_step_failure(step, verification, attempts)
            return StepResult.failure_result(
                step=step,
                verification=verification,
                execution=last_execution,
                attempts=attempts,
            )

        verification = Verification.fail(evidence="step exceeded retry budget")
        self._emit_step_failure(step, verification, attempts)
        return StepResult.failure_result(
            step=step,
            verification=verification,
            execution=last_execution,
            attempts=attempts,
        )

    def _emit_step_failure(
        self,
        step: PlanStep,
        verification: Verification,
        attempts: int,
    ) -> None:
        if self.telemetry_emit is None:
            return
        self.telemetry_emit(
            "pev_step_failed",
            {
                "plan_step_id": step.id,
                "verdict": verification.verdict.value,
                "next_action": verification.next_action,
                "attempts": attempts,
            },
        )

    @staticmethod
    async def _default_ask_user_handler(
        plan: Plan,
        step: PlanStep,
        verification: Verification,
    ) -> bool:
        return False


def _response_content(response: Any) -> str:
    if isinstance(response, str):
        return response
    content = getattr(response, "content", None)
    return str(content or "")


def _normalize_next_action(value: object, verdict_raw: str) -> NextAction:
    action = str(value or "").strip().lower()
    if action in {"proceed", "continue", "pass"}:
        return "continue"
    if action == "retry_step":
        return "retry_step"
    if action in {"rollback", "abort_plan", "abort"}:
        return "abort_plan"
    if action == "ask_user":
        return "ask_user"
    if verdict_raw == "uncertain":
        return "ask_user"
    if verdict_raw == "pass":
        return "continue"
    return "abort_plan"


def _safe_step_id(value: str, *, fallback: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value)
    safe = safe.strip("-_").lower()
    return safe or fallback


def _stringify_execution(execution: Any) -> str:
    if isinstance(execution, str):
        return execution
    try:
        return json.dumps(execution, sort_keys=True, default=str)
    except TypeError:
        return str(execution)


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value
