"""Schema for AI-driven verification harness scenarios and run artifacts.

Scenario lifecycle:
  generate_scenario.py  ->  ScenarioSpec (frozen JSON)
  run_scenario.py       ->  runs agent, writes RunMeta + transcript + diff
  grade_run.py          ->  writes GradingReport

Artifact layout per run:
  autocode/docs/qa/test-results/ai-verification/<run_id>/
    scenario.json         frozen ScenarioSpec input
    repo_seed/            copy of repo state before agent execution
    agent_transcript.jsonl  raw agent stdout/stderr per turn (one JSON object per line)
    diff.patch            git diff --stat + patch after agent run
    test_log.txt          deterministic check combined stdout/stderr
    grading_report.json   GradingReport (deterministic results + verdict)
    review.md             AI reviewer narrative (when ai_review_enabled)
    meta.json             RunMeta (timings, exit status, wall time)
  autocode/docs/qa/test-results/ai-verification/index.md  summary table
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal


SCHEMA_VERSION = "1"

QA_BASE = Path("autocode/docs/qa/test-results/ai-verification")
SANDBOX_BASE = Path("sandboxes/ai-verification")
FIXTURES_DIR = Path("benchmarks/ai_verification/fixtures")


class Category(str, Enum):
    BACKEND_FEATURE = "backend_feature"
    FRONTEND_FEATURE = "frontend_feature"
    REFACTOR = "refactor"
    MIGRATION = "migration"
    DIRTY_CLEANUP = "dirty_cleanup"
    REPO_INIT = "repo_init"
    LONG_HORIZON = "long_horizon"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class SeedMode(str, Enum):
    FRESH = "fresh"      # init brand-new empty repo
    FIXTURE = "fixture"  # copy from fixtures/<fixture_ref>/
    MUTATE = "mutate"    # copy fixture then apply injections on top


class Check(str, Enum):
    RUN_TESTS = "run_tests"
    LINT = "lint"
    TYPECHECK = "typecheck"
    BUILD = "build"
    SNAPSHOT = "snapshot"


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    INFRA_FAIL = "INFRA_FAIL"


@dataclass
class TargetStack:
    language: str            # "python" | "typescript" | "rust" | "go" | ...
    framework: str = ""      # "fastapi" | "react" | "" | ...
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Injection:
    """A single file to write into the sandbox repo before the agent runs."""
    path: str    # relative to sandbox repo root
    content: str


@dataclass
class RepoSeed:
    mode: SeedMode = SeedMode.FRESH
    fixture_ref: str = ""                         # subdirectory under FIXTURES_DIR
    injections: list[Injection] = field(default_factory=list)
    setup_commands: list[str] = field(default_factory=list)


@dataclass
class TaskSpec:
    prompt: str                                   # shown verbatim to agent
    required_artifacts: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    followup_prompts: list[str] = field(default_factory=list)  # scripted human turns (index 0 = turn 2 prompt)


@dataclass
class GradingSpec:
    checks: list[Check] = field(default_factory=lambda: [Check.RUN_TESTS])
    check_commands: dict[str, str] = field(default_factory=dict)  # check -> shell cmd
    ai_review_enabled: bool = True
    reviewer: Literal["codex", "claude"] = "claude"
    expect_fixture_failure: bool | None = None


@dataclass
class ScenarioSpec:
    """Frozen scenario definition. Serialized to scenario.json before agent run."""
    category: Category
    difficulty: Difficulty
    title: str
    description: str
    task_spec: TaskSpec
    target_stack: TargetStack
    repo_seed: RepoSeed = field(default_factory=RepoSeed)
    grading: GradingSpec = field(default_factory=GradingSpec)
    duration_hint_minutes: int = 15
    scenario_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: str = SCHEMA_VERSION
    generated_by: Literal["human", "codex", "claude"] = "human"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    seed: int = 0
    expected_outcomes: dict[str, list[str]] = field(default_factory=lambda: {"must_have": [], "must_not_have": []})
    trajectory_assertions: dict[str, Any] = field(default_factory=dict)
    artifact_assertions: dict[str, Any] = field(default_factory=dict)
    turn_assertions: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str))

    @classmethod
    def load(cls, path: Path) -> ScenarioSpec:
        if path.suffix.lower() in {".yaml", ".yml"}:
            from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml_file

            return load_scenario_yaml_file(path)
        return scenario_from_dict(json.loads(path.read_text()))


@dataclass
class CheckResult:
    check: Check
    passed: bool
    command: str
    output: str
    exit_code: int


@dataclass
class GradingReport:
    verdict: Verdict
    check_results: list[CheckResult]
    ai_review_enabled: bool
    ai_verdict: str = ""
    ai_reasoning: str = ""
    ai_reviewer: str = ""
    trajectory_passed: bool | None = None
    artifact_passed: bool | None = None
    turn_passed: bool | None = None
    artifact_results: list[dict[str, Any]] = field(default_factory=list)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2, default=str))

    @property
    def deterministic_passed(self) -> bool:
        return all(r.passed for r in self.check_results)


@dataclass
class RunMeta:
    run_id: str
    scenario_id: str
    agent: str
    status: str
    started_at: str
    finished_at: str
    wall_time_s: float
    exit_status: int
    tool_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    error: str = ""
    infra_fail_reason: str = ""

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2, default=str))


def artifact_dir(run_id: str, base: Path | None = None) -> Path:
    return (base or QA_BASE) / run_id


def sandbox_dir(run_id: str, base: Path | None = None) -> Path:
    return (base or SANDBOX_BASE) / run_id


def new_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    short = str(uuid.uuid4())[:8]
    return f"{ts}-{short}"


# --------------------------------------------------------------------------- #
# De-serialization helpers                                                     #
# --------------------------------------------------------------------------- #

def scenario_from_dict(d: dict[str, Any]) -> ScenarioSpec:
    stack = d.get("target_stack", {})
    seed_raw = d.get("repo_seed", {})
    injections = [Injection(**i) for i in seed_raw.get("injections", [])]
    # Support shorthand: "files": {"path": "content"} → injections list
    for path, content in seed_raw.get("files", {}).items():
        injections.append(Injection(path=path, content=content))
    repo_seed = RepoSeed(
        mode=SeedMode(seed_raw.get("mode", SeedMode.FRESH)),
        fixture_ref=seed_raw.get("fixture_ref", ""),
        injections=injections,
        setup_commands=seed_raw.get("setup_commands", []),
    )
    task_raw = d.get("task_spec", {})
    task_spec = TaskSpec(
        prompt=task_raw["prompt"],
        required_artifacts=task_raw.get("required_artifacts", []),
        success_criteria=task_raw.get("success_criteria", []),
        followup_prompts=task_raw.get("followup_prompts", []),
    )
    grading_raw = d.get("grading", {})
    _eff_raw = grading_raw.get("expect_fixture_failure", None)
    grading = GradingSpec(
        checks=[Check(c) for c in grading_raw.get("checks", [Check.RUN_TESTS])],
        check_commands=grading_raw.get("check_commands", {}),
        ai_review_enabled=grading_raw.get("ai_review_enabled", True),
        reviewer=grading_raw.get("reviewer", "claude"),
        expect_fixture_failure=_eff_raw if _eff_raw is not None else None,
    )
    return ScenarioSpec(
        category=Category(d["category"]),
        difficulty=Difficulty(d["difficulty"]),
        title=d["title"],
        description=d["description"],
        task_spec=task_spec,
        target_stack=TargetStack(
            language=stack.get("language", ""),
            framework=stack.get("framework", ""),
            extra=stack.get("extra", {}),
        ),
        repo_seed=repo_seed,
        grading=grading,
        duration_hint_minutes=d.get("duration_hint_minutes", 15),
        scenario_id=d.get("scenario_id", str(uuid.uuid4())),
        schema_version=d.get("schema_version", SCHEMA_VERSION),
        generated_by=d.get("generated_by", "human"),
        created_at=d.get("created_at", ""),
        seed=d.get("seed", 0),
        expected_outcomes=d.get("expected_outcomes", {"must_have": [], "must_not_have": []}),
        trajectory_assertions=d.get("trajectory_assertions", {}),
        artifact_assertions=d.get("artifact_assertions", {}),
        turn_assertions=d.get("turn_assertions", {}),
    )
