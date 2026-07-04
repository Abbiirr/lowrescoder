"""Deterministic proof for P3b PEV/Ralph quantitative gates."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _setup_path() -> None:
    if str(_PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(_PROJECT_ROOT))
    src = _PROJECT_ROOT / "autocode" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def verify_p3b_reliability_criteria() -> list[str]:
    """Return errors if P3b quantitative gates are not met."""

    _setup_path()

    from autocode.agent.pev import PEVRunner, Plan, PlanStep, Verification
    from autocode.agent.ralph_loop import RalphAgentState, RalphLoop
    from autocode.session.intent_store import Intent

    errors: list[str] = []

    total_failing_plans = 10
    caught_failing_plans = 0
    for idx in range(total_failing_plans):
        plan = Plan(
            goal=f"repair failing fixture {idx}",
            steps=[
                PlanStep(
                    id=f"repair-{idx}",
                    description="Run tests and repair the failing fixture",
                    success_predicate="tests pass",
                    failure_predicate="pytest reports failures",
                )
            ],
        )

        def executor(step: PlanStep, feedback: str | None) -> dict[str, str]:
            return {
                "step": step.id,
                "test_log": "FAILED test_example.py::test_contract",
                "feedback": feedback or "",
            }

        def verifier(step: PlanStep, execution: object) -> Verification:
            del step
            if "FAILED" in str(execution):
                return Verification.fail(
                    evidence="detected failing test output",
                    next_action="abort_plan",
                    feedback="repair before continuing",
                )
            return Verification.pass_(evidence="no failure marker")

        result = PEVRunner(executor=executor, verifier=verifier).execute_plan(plan)
        if result.status == "failed":
            caught_failing_plans += 1

    pev_ratio = caught_failing_plans / total_failing_plans
    if pev_ratio < 0.50:
        errors.append(
            f"FAIL: PEV caught {pev_ratio:.2f} of failing plans; required >= 0.50 "
            f"({caught_failing_plans}/{total_failing_plans})"
        )

    total_context_limit_sessions = 10
    recovered_context_limit_sessions = 0
    for idx in range(total_context_limit_sessions):
        intent = Intent(
            session_id=f"session-{idx}",
            original_goal="finish the long-horizon task",
            captured_at="2026-05-04T00:00:00Z",
            success_criteria=["recovery message injected"],
            constraints=["do not abandon the task"],
            progress_so_far=["initial work completed"],
        )
        result = RalphLoop().maybe_recover(
            intent,
            RalphAgentState(
                turn_index=idx + 2,
                assistant_message="",
                tool_calls_last_turn=0,
                zero_tool_turns=3,
                context_fraction=0.91,
            ),
        )
        if result.recovered:
            recovered_context_limit_sessions += 1

    ralph_ratio = recovered_context_limit_sessions / total_context_limit_sessions
    if ralph_ratio < 0.80:
        errors.append(
            f"FAIL: Ralph recovered {ralph_ratio:.2f} of context-limit sessions; "
            f"required >= 0.80 "
            f"({recovered_context_limit_sessions}/{total_context_limit_sessions})"
        )

    return errors


def run_check() -> None:
    errors = verify_p3b_reliability_criteria()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        sys.exit(1)
    print("PASS: P3b PEV/Ralph quantitative criteria met")
    sys.exit(0)


if __name__ == "__main__":
    run_check()
