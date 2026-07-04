"""Static lint checks for AI verification scenarios."""

from __future__ import annotations

from dataclasses import dataclass

from benchmarks.ai_verification.schema import ScenarioSpec


@dataclass(frozen=True)
class ScenarioLintFinding:
    code: str
    path: str
    detail: str


def lint_seeded_test_protection(scenario: ScenarioSpec) -> list[ScenarioLintFinding]:
    """Flag seeded visible tests that can be rewritten to fake a pass.

    A visible seeded test file is acceptable only if the scenario either marks
    it immutable with ``must_not_change_files`` or provides hidden tests.
    """

    hidden_tests = scenario.artifact_assertions.get("hidden_test_files", {})
    protected_paths = set(scenario.artifact_assertions.get("must_not_change_files", []))
    if hidden_tests:
        return []

    findings: list[ScenarioLintFinding] = []
    for injection in scenario.repo_seed.injections:
        if _is_seeded_visible_test(injection.path) and injection.path not in protected_paths:
            findings.append(
                ScenarioLintFinding(
                    code="seeded_test_unprotected",
                    path=injection.path,
                    detail=(
                        "Seeded visible test files must be protected with "
                        "artifact_assertions.must_not_change_files or hidden tests."
                    ),
                )
            )
    return findings


def _is_seeded_visible_test(path: str) -> bool:
    normalized = path.replace("\\", "/")
    name = normalized.rsplit("/", 1)[-1]
    if not name.endswith(".py"):
        return False
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or normalized.startswith("tests/")
    )
