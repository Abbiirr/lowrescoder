"""E2E-BugFix scenario: Fix failing tests in a seeded broken project.

The agent is given a project with intentionally broken tests and must
diagnose the issues and fix them without breaking passing tests.

Scoring focuses on:
- Correctness: all previously-failing tests now pass
- Precision: no previously-passing tests broken
- Minimal changes: fewer lines changed is better
"""

from __future__ import annotations

from pathlib import Path

from e2e.scenario_contract import AcceptanceCheck, ScenarioManifest

SCENARIO_ID = "E2E-BugFix"

MANIFEST = ScenarioManifest(
    scenario_id=SCENARIO_ID,
    name="Bug-Fix Benchmark",
    description=(
        "Fix failing tests in a seeded broken JavaScript project. "
        "The project has 3 intentionally broken test cases that the agent "
        "must diagnose and fix without breaking existing passing tests."
    ),
    prompt=(
        "This project has failing tests. Run `npm test` to see which tests "
        "are failing, then fix the code so all tests pass. Do NOT modify the "
        "test files — only fix the source code. Keep changes minimal."
    ),
    follow_ups=[
        "Run `npm test` again to verify all tests pass. If any still fail, "
        "continue fixing the source code.",
    ],
    expected_files=["package.json", "src/index.js"],
    expected_commands=["npm test"],
    acceptance_checks=[
        AcceptanceCheck(
            name="all_tests_pass",
            command="npm test",
            timeout_s=60,
            required=True,
        ),
    ],
    max_score=100,
    scoring_categories={
        "tests_fixed": 50,
        "no_regressions": 25,
        "minimal_changes": 15,
        "code_quality": 10,
    },
    max_wall_time_s=600,
    max_tool_calls=50,
    max_turns=3,
    min_score=60,
    strict_min_score=80,
    language="javascript",
    tags=["bugfix", "deterministic", "regression-lane"],
    seed_fixture=Path(__file__).resolve().parent.parent / "fixtures" / "bugfix-seed",
    setup_commands=["npm install"],
    required_artifacts=["package.json", "src/index.js"],
)
