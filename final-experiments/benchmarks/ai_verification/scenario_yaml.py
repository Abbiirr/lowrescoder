"""YAML scenario loader for AI verification harness.

Loads human-friendly YAML scenario definitions and converts them to
ScenarioSpec objects used by the existing harness pipeline.

YAML schema reuses existing ScenarioSpec fields plus an ``expected_outcomes``
extension for NDJSON grader predicates.  The YAML format is intentionally
a subset of the existing ScenarioSpec JSON schema for easy round-tripping.

Expected YAML structure::

    title: <str>
    category: <Category enum value>
    difficulty: <Difficulty enum value>
    target_stack:
      language: <str>
      framework: <str>        # optional
    task_spec:
      prompt: <str>
      required_artifacts: []   # optional
      success_criteria: []     # optional
    expected_outcomes:         # optional
      must_have: []
      must_not_have: []
    grading:                   # optional
      checks: [run_tests, lint, ...]
      check_commands: {}       # optional
    repo_seed:                 # optional
      mode: fresh|fixture|mutate
      fixture_ref: <str>
      injections: []
      setup_commands: []
"""

from __future__ import annotations

from pathlib import Path

import yaml

from benchmarks.ai_verification.schema import (
    Category,
    Check,
    Difficulty,
    GradingSpec,
    Injection,
    RepoSeed,
    ScenarioSpec,
    SeedMode,
    TargetStack,
    TaskSpec,
)


def load_scenario_yaml(yaml_text: str) -> ScenarioSpec:
    raw = yaml.safe_load(yaml_text)
    if not isinstance(raw, dict):
        raise ValueError("YAML scenario must be a mapping")
    return _yaml_dict_to_spec(raw)


def load_scenario_yaml_file(path: Path) -> ScenarioSpec:
    return load_scenario_yaml(path.read_text(encoding="utf-8"))


def _yaml_dict_to_spec(raw: dict) -> ScenarioSpec:
    if "category" not in raw:
        raise ValueError("YAML scenario missing required field: category")
    if "title" not in raw:
        raise ValueError("YAML scenario missing required field: title")
    if "task_spec" not in raw:
        raise ValueError("YAML scenario missing required field: task_spec")

    try:
        Category(raw["category"])
    except ValueError:
        raise ValueError(f"Invalid category: {raw['category']!r}") from None

    try:
        Difficulty(raw.get("difficulty", "easy"))
    except ValueError:
        raise ValueError(f"Invalid difficulty: {raw['difficulty']!r}") from None

    stack_raw = raw.get("target_stack", {})
    task_raw = raw["task_spec"]
    seed_raw = raw.get("repo_seed", {})
    grading_raw = raw.get("grading", {})

    injections = [Injection(**i) for i in seed_raw.get("injections", [])]
    for path, content in seed_raw.get("files", {}).items():
        injections.append(Injection(path=path, content=content))
    repo_seed = RepoSeed(
        mode=SeedMode(seed_raw.get("mode", SeedMode.FRESH)),
        fixture_ref=seed_raw.get("fixture_ref", ""),
        injections=injections,
        setup_commands=seed_raw.get("setup_commands", []),
    )
    task_spec = TaskSpec(
        prompt=task_raw["prompt"],
        required_artifacts=task_raw.get("required_artifacts", []),
        success_criteria=task_raw.get("success_criteria", []),
        followup_prompts=task_raw.get("followup_prompts", []),
    )
    _eff_raw = grading_raw.get("expect_fixture_failure", None)
    grading = GradingSpec(
        checks=[Check(c) for c in grading_raw.get("checks", [Check.RUN_TESTS])],
        check_commands=grading_raw.get("check_commands", {}),
        ai_review_enabled=grading_raw.get("ai_review_enabled", False),
        reviewer=grading_raw.get("reviewer", "claude"),
        expect_fixture_failure=_eff_raw if _eff_raw is not None else None,
    )
    target_stack = TargetStack(
        language=stack_raw.get("language", ""),
        framework=stack_raw.get("framework", ""),
        extra=stack_raw.get("extra", {}),
    )
    expected_outcomes = raw.get("expected_outcomes", {"must_have": [], "must_not_have": []})

    return ScenarioSpec(
        category=Category(raw["category"]),
        difficulty=Difficulty(raw.get("difficulty", "easy")),
        title=raw["title"],
        description=raw.get("description", raw["title"]),
        task_spec=task_spec,
        target_stack=target_stack,
        repo_seed=repo_seed,
        grading=grading,
        duration_hint_minutes=raw.get("duration_hint_minutes", 15),
        expected_outcomes=expected_outcomes,
        trajectory_assertions=raw.get("trajectory_assertions", {}),
        artifact_assertions=raw.get("artifact_assertions", {}),
        turn_assertions=raw.get("turn_assertions", {}),
    )
