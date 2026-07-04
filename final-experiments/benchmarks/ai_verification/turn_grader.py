"""Turn-level assertion grader for AI verification harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TurnAssertionResult:
    assertion: str
    passed: bool
    detail: str = ""


@dataclass
class TurnReport:
    passed: bool
    results: list[TurnAssertionResult] = field(default_factory=list)

    @property
    def failures(self) -> list[TurnAssertionResult]:
        return [r for r in self.results if not r.passed]


def grade_turns(
    *,
    turn_count: int,
    turns: list[dict[str, Any]],
    assertions: dict[str, Any],
) -> TurnReport:
    results: list[TurnAssertionResult] = []

    min_turns = assertions.get("min_turns")
    if min_turns is not None:
        if turn_count >= int(min_turns):
            results.append(TurnAssertionResult("min_turns", True))
        else:
            results.append(TurnAssertionResult(
                "min_turns",
                False,
                f"expected >= {min_turns} turns, got {turn_count}",
            ))

    max_turns = assertions.get("max_turns")
    if max_turns is not None:
        if turn_count <= int(max_turns):
            results.append(TurnAssertionResult("max_turns", True))
        else:
            results.append(TurnAssertionResult(
                "max_turns",
                False,
                f"expected <= {max_turns} turns, got {turn_count}",
            ))

    if assertions.get("no_regression_after_pass"):
        first_pass_idx = None
        for idx, turn in enumerate(turns):
            if turn.get("grading_passed") is True:
                first_pass_idx = idx
                break
        if first_pass_idx is None:
            results.append(TurnAssertionResult(
                "no_regression_after_pass",
                False,
                "no passing turn observed",
            ))
        else:
            regressions = [
                t.get("turn", idx + 1)
                for idx, t in enumerate(turns[first_pass_idx + 1:], start=first_pass_idx + 1)
                if (
                    t.get("grading_passed") is False
                    and not t.get("scope_changed_after_pass")
                )
            ]
            if regressions:
                results.append(TurnAssertionResult(
                    "no_regression_after_pass",
                    False,
                    f"turns regressed after first pass: {regressions}",
                ))
            else:
                results.append(TurnAssertionResult("no_regression_after_pass", True))

    if assertions.get("require_at_least_one_passing_turn"):
        if any(turn.get("grading_passed") is True for turn in turns):
            results.append(TurnAssertionResult("require_at_least_one_passing_turn", True))
        else:
            results.append(TurnAssertionResult(
                "require_at_least_one_passing_turn",
                False,
                "no passing turn observed",
            ))

    return TurnReport(passed=all(r.passed for r in results), results=results)
