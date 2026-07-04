"""Trajectory grader for AI verification harness.

Deterministic grader that checks tool-call sequences against scenario
trajectory assertions. Supports exact, in-order, any-order, and family
matching modes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

_TOOL_EQUIVALENT_FAMILIES: dict[str, set[str]] = {
    # Some agents create fresh files with write_file/apply_patch instead of
    # edit_file. For scenario contracts that only need code mutation evidence,
    # any successful file-write tool satisfies the edit_file requirement.
    "edit_file": {"file_write"},
}


@dataclass
class TrajectoryAssertionResult:
    assertion: str
    passed: bool
    detail: str = ""


@dataclass
class TrajectoryReport:
    passed: bool
    results: list[TrajectoryAssertionResult] = field(default_factory=list)

    @property
    def failures(self) -> list[TrajectoryAssertionResult]:
        return [r for r in self.results if not r.passed]


def grade_trajectory(
    tool_calls: list[dict],
    assertions: dict,
) -> TrajectoryReport:
    results: list[TrajectoryAssertionResult] = []

    tool_names = [tc.get("tool_name", "") for tc in tool_calls]
    tool_families = [tc.get("tool_family", "") for tc in tool_calls]

    must_use = assertions.get("must_use_tools", [])
    if must_use:
        missing = [
            t for t in must_use
            if not _tool_requirement_satisfied(t, tool_names, tool_families)
        ]
        if missing:
            results.append(TrajectoryAssertionResult(
                assertion="must_use_tools",
                passed=False,
                detail=f"missing tools: {missing}",
            ))
        else:
            results.append(TrajectoryAssertionResult(
                assertion="must_use_tools",
                passed=True,
            ))

    must_not = assertions.get("must_not_use_tools", [])
    if must_not:
        forbidden_used = [t for t in must_not if t in tool_names]
        if forbidden_used:
            results.append(TrajectoryAssertionResult(
                assertion="must_not_use_tools",
                passed=False,
                detail=f"forbidden tools used: {forbidden_used}",
            ))
        else:
            results.append(TrajectoryAssertionResult(
                assertion="must_not_use_tools",
                passed=True,
            ))

    must_families = assertions.get("must_use_tool_families", [])
    if must_families:
        missing = [f for f in must_families if f not in tool_families]
        if missing:
            results.append(TrajectoryAssertionResult(
                assertion="must_use_tool_families",
                passed=False,
                detail=f"missing families: {missing}",
            ))
        else:
            results.append(TrajectoryAssertionResult(
                assertion="must_use_tool_families",
                passed=True,
            ))

    in_order = assertions.get("in_order_tools", [])
    if in_order:
        if _subsequence(tool_names, in_order):
            results.append(TrajectoryAssertionResult(
                assertion="in_order_tools",
                passed=True,
            ))
        else:
            results.append(TrajectoryAssertionResult(
                assertion="in_order_tools",
                passed=False,
                detail=f"tools {in_order} not found in order in {tool_names}",
            ))

    any_order = assertions.get("any_order_tools", [])
    if any_order:
        missing = [t for t in any_order if t not in tool_names]
        if missing:
            results.append(TrajectoryAssertionResult(
                assertion="any_order_tools",
                passed=False,
                detail=f"missing tools: {missing}",
            ))
        else:
            results.append(TrajectoryAssertionResult(
                assertion="any_order_tools",
                passed=True,
            ))

    exact = assertions.get("exact_tools", [])
    if exact:
        if tool_names == exact:
            results.append(TrajectoryAssertionResult(
                assertion="exact_tools",
                passed=True,
            ))
        else:
            results.append(TrajectoryAssertionResult(
                assertion="exact_tools",
                passed=False,
                detail=f"expected {exact}, got {tool_names}",
            ))

    min_calls = assertions.get("min_tool_calls")
    if min_calls is not None:
        if len(tool_names) >= min_calls:
            results.append(TrajectoryAssertionResult(
                assertion="min_tool_calls",
                passed=True,
            ))
        else:
            results.append(TrajectoryAssertionResult(
                assertion="min_tool_calls",
                passed=False,
                detail=f"expected >= {min_calls}, got {len(tool_names)}",
            ))

    max_calls = assertions.get("max_tool_calls")
    if max_calls is not None:
        if len(tool_names) <= max_calls:
            results.append(TrajectoryAssertionResult(
                assertion="max_tool_calls",
                passed=True,
            ))
        else:
            results.append(TrajectoryAssertionResult(
                assertion="max_tool_calls",
                passed=False,
                detail=f"expected <= {max_calls}, got {len(tool_names)}",
            ))

    max_by_name = assertions.get("max_tool_calls_by_name", {})
    if isinstance(max_by_name, dict):
        for tool_name, limit in max_by_name.items():
            observed = sum(1 for name in tool_names if name == tool_name)
            if observed <= int(limit):
                results.append(TrajectoryAssertionResult(
                    assertion=f"max_tool_calls_by_name({tool_name})",
                    passed=True,
                ))
            else:
                results.append(TrajectoryAssertionResult(
                    assertion=f"max_tool_calls_by_name({tool_name})",
                    passed=False,
                    detail=f"expected <= {int(limit)} {tool_name} calls, got {observed}",
                ))

    max_failed = assertions.get("max_failed_tool_calls")
    if max_failed is not None:
        failed_count = sum(1 for tc in tool_calls if tc.get("status") == "error")
        if failed_count <= max_failed:
            results.append(TrajectoryAssertionResult(
                assertion="max_failed_tool_calls",
                passed=True,
            ))
        else:
            results.append(TrajectoryAssertionResult(
                assertion="max_failed_tool_calls",
                passed=False,
                detail=f"expected <= {max_failed} failed, got {failed_count}",
            ))

    all_passed = all(r.passed for r in results)
    return TrajectoryReport(passed=all_passed, results=results)


def _subsequence(seq: list[str], sub: list[str]) -> bool:
    it = iter(seq)
    return all(item in it for item in sub)


def _tool_requirement_satisfied(
    required_tool: str,
    tool_names: list[str],
    tool_families: list[str],
) -> bool:
    if required_tool in tool_names:
        return True
    equivalent_families = _TOOL_EQUIVALENT_FAMILIES.get(required_tool, set())
    return any(family in tool_families for family in equivalent_families)
