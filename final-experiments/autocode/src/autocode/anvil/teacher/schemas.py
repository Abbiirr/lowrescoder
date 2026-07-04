"""Typed schemas for teacher mode (PLAN_04 §1.1/§1.2, §4.2.1/§4.3 of 04_ARCHITECTURE).

These are the load-bearing data contracts shared by the recorder, the verifier,
the classifier and the reflector. They are intentionally dependency-free
(stdlib ``dataclasses`` + ``enum`` + ``json``) and serialise to *exactly* the
field names the architecture corpus normatively specifies, so the JSON is a
stable interchange format with the offline loop and the eval flywheel.

Note on the ``class`` field: the root-cause taxonomy key is the JSON literal
``"class"`` (a Python reserved word), so it is stored on the dataclass as
``category`` and mapped to/from ``"class"`` at the (de)serialisation boundary.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

# --------------------------------------------------------------------------- #
# Enums                                                                        #
# --------------------------------------------------------------------------- #


class TaskSource(StrEnum):
    """Where a task came from (trajectory.task.source)."""

    USER_SESSION = "user_session"
    TERMINAL_BENCH = "terminal_bench"
    SYNTHETIC = "synthetic"


class Layer(StrEnum):
    """The escalation layer a step ran at."""

    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"


class VerdictLabel(StrEnum):
    """The deterministic outcome label (verifier §4.3)."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAIL = "fail"
    ERROR = "error"


class OracleStrength(StrEnum):
    """How decisive the executable oracle was for this case (§8.1)."""

    STRONG = "strong"  # a real test suite decided it
    WEAK = "weak"  # only build/lint/types, or judge-only (e.g. docstring change)


# --------------------------------------------------------------------------- #
# Trajectory (§4.2.1)                                                          #
# --------------------------------------------------------------------------- #


@dataclass
class Task:
    instruction: str
    repo: str = ""
    commit: str = ""
    source: str = TaskSource.SYNTHETIC.value

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Task:
        return cls(
            instruction=d.get("instruction", ""),
            repo=d.get("repo", ""),
            commit=d.get("commit", ""),
            source=d.get("source", TaskSource.SYNTHETIC.value),
        )


@dataclass
class ModelInfo:
    alias: str = ""
    provider: str = ""
    is_local: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ModelInfo:
        return cls(
            alias=d.get("alias", ""),
            provider=d.get("provider", ""),
            is_local=bool(d.get("is_local", False)),
        )


@dataclass
class Step:
    """One step in a trajectory (§4.2.1.steps[])."""

    i: int
    layer: str = Layer.L4.value
    action: str = ""  # retrieve | tool_call | plan | generate | escalate
    tool: str = ""
    args: dict[str, Any] = field(default_factory=dict)
    observation_digest: str = ""
    tokens: dict[str, int] = field(default_factory=lambda: {"in": 0, "out": 0})
    latency_ms: int = 0
    escalated_from: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Step:
        return cls(
            i=int(d.get("i", 0)),
            layer=d.get("layer", Layer.L4.value),
            action=d.get("action", ""),
            tool=d.get("tool", ""),
            args=dict(d.get("args", {}) or {}),
            observation_digest=d.get("observation_digest", ""),
            tokens=dict(d.get("tokens", {"in": 0, "out": 0}) or {"in": 0, "out": 0}),
            latency_ms=int(d.get("latency_ms", 0)),
            escalated_from=d.get("escalated_from"),
        )


@dataclass
class TestResults:
    __test__ = False  # not a pytest test class despite the "Test" prefix

    passed: int = 0
    failed: int = 0
    regressed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TestResults:
        return cls(
            passed=int(d.get("passed", 0)),
            failed=int(d.get("failed", 0)),
            regressed=int(d.get("regressed", 0)),
        )


@dataclass
class Verdict:
    """The deterministic executable verdict (§4.3) — the teacher's oracle/anchor."""

    diff_applies: bool = False
    build_passed: bool = False
    tests: TestResults = field(default_factory=TestResults)
    lint_clean: bool = False
    types_clean: bool = False
    label: str = VerdictLabel.ERROR.value
    oracle_strength: str = OracleStrength.WEAK.value

    def to_dict(self) -> dict[str, Any]:
        return {
            "diff_applies": self.diff_applies,
            "build_passed": self.build_passed,
            "tests": self.tests.to_dict(),
            "lint_clean": self.lint_clean,
            "types_clean": self.types_clean,
            "label": self.label,
            "oracle_strength": self.oracle_strength,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Verdict:
        return cls(
            diff_applies=bool(d.get("diff_applies", False)),
            build_passed=bool(d.get("build_passed", False)),
            tests=TestResults.from_dict(d.get("tests", {}) or {}),
            lint_clean=bool(d.get("lint_clean", False)),
            types_clean=bool(d.get("types_clean", False)),
            label=d.get("label", VerdictLabel.ERROR.value),
            oracle_strength=d.get("oracle_strength", OracleStrength.WEAK.value),
        )

    @property
    def is_success(self) -> bool:
        return self.label == VerdictLabel.SUCCESS.value


@dataclass
class Trajectory:
    """A typed record of one task run (§4.2.1)."""

    trajectory_id: str
    task: Task
    harness_version: str = ""
    model: ModelInfo = field(default_factory=ModelInfo)
    steps: list[Step] = field(default_factory=list)
    final_diff: str | None = None
    outcome: Verdict = field(default_factory=Verdict)
    cost: dict[str, float] = field(default_factory=lambda: {"usd": 0.0, "wall_s": 0.0})
    layer_distribution: dict[str, float] = field(
        default_factory=lambda: {"L1": 0.0, "L2": 0.0, "L3": 0.0, "L4": 0.0}
    )
    role: str = "student"  # "student" | "teacher" — Anvil annotation (not in §4.2.1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trajectory_id": self.trajectory_id,
            "task": self.task.to_dict(),
            "harness_version": self.harness_version,
            "model": self.model.to_dict(),
            "steps": [s.to_dict() for s in self.steps],
            "final_diff": self.final_diff,
            "outcome": self.outcome.to_dict(),
            "cost": dict(self.cost),
            "layer_distribution": dict(self.layer_distribution),
            "role": self.role,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Trajectory:
        return cls(
            trajectory_id=d.get("trajectory_id", ""),
            task=Task.from_dict(d.get("task", {}) or {}),
            harness_version=d.get("harness_version", ""),
            model=ModelInfo.from_dict(d.get("model", {}) or {}),
            steps=[Step.from_dict(s) for s in (d.get("steps", []) or [])],
            final_diff=d.get("final_diff"),
            outcome=Verdict.from_dict(d.get("outcome", {}) or {}),
            cost=dict(d.get("cost", {"usd": 0.0, "wall_s": 0.0}) or {}),
            layer_distribution=dict(
                d.get("layer_distribution", {"L1": 0.0, "L2": 0.0, "L3": 0.0, "L4": 0.0}) or {}
            ),
            role=d.get("role", "student"),
        )

    def compute_layer_distribution(self) -> dict[str, float]:
        """(Re)derive the fraction of steps spent per layer from ``steps``."""
        counts = {layer.value: 0 for layer in Layer}
        for step in self.steps:
            counts[step.layer] = counts.get(step.layer, 0) + 1
        total = sum(counts.values()) or 1
        dist = {k: round(v / total, 4) for k, v in counts.items()}
        self.layer_distribution = dist
        return dist

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, text: str) -> Trajectory:
        return cls.from_dict(json.loads(text))


# --------------------------------------------------------------------------- #
# Teaching packet (§1.2 / §6.0)                                               #
# --------------------------------------------------------------------------- #


@dataclass
class RootCause:
    category: str  # serialised as "class" — one of taxonomy.RootCauseClass values
    evidence_step: int = -1
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "class": self.category,
            "evidence_step": self.evidence_step,
            "explanation": self.explanation,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RootCause:
        return cls(
            category=d.get("class", d.get("category", "")),
            evidence_step=int(d.get("evidence_step", -1)),
            explanation=d.get("explanation", ""),
        )


@dataclass
class ScoreBreakdown:
    """Executable-first rubric (§2). ``style_judge`` is the only secondary signal."""

    diff_applies: float = 0.0
    build: float = 0.0
    tests: float = 0.0
    lint: float = 0.0
    types: float = 0.0
    style_judge: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ScoreBreakdown:
        return cls(
            diff_applies=float(d.get("diff_applies", 0.0)),
            build=float(d.get("build", 0.0)),
            tests=float(d.get("tests", 0.0)),
            lint=float(d.get("lint", 0.0)),
            types=float(d.get("types", 0.0)),
            style_judge=float(d.get("style_judge", 0.0)),
        )


@dataclass
class HarnessFix:
    """The actionable offline output: a candidate manifest edit."""

    target: str  # manifest component id, e.g. "tool.callgraph.impl"
    kind: str  # tool_implementation | tool_description | middleware | ... | distilled_adapter
    sketch: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> HarnessFix:
        return cls(
            target=d.get("target", ""),
            kind=d.get("kind", ""),
            sketch=d.get("sketch", ""),
        )


@dataclass
class Provenance:
    teacher_model: str = ""
    anvil_version: str = ""
    created: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Provenance:
        return cls(
            teacher_model=d.get("teacher_model", ""),
            anvil_version=d.get("anvil_version", ""),
            created=d.get("created", ""),
        )


@dataclass
class TeachingPacket:
    """The teacher's typed output (§1.2 / §6.0)."""

    packet_id: str
    trajectory_id: str
    verdict: Verdict
    root_cause: RootCause
    score_breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    revision: str | None = None
    harness_fix: HarnessFix | None = None
    playbook_delta: str | None = None
    provenance: Provenance = field(default_factory=Provenance)

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "trajectory_id": self.trajectory_id,
            "verdict": self.verdict.to_dict(),
            "root_cause": self.root_cause.to_dict(),
            "score_breakdown": self.score_breakdown.to_dict(),
            "revision": self.revision,
            "harness_fix": self.harness_fix.to_dict() if self.harness_fix else None,
            "playbook_delta": self.playbook_delta,
            "provenance": self.provenance.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TeachingPacket:
        hf = d.get("harness_fix")
        return cls(
            packet_id=d.get("packet_id", ""),
            trajectory_id=d.get("trajectory_id", ""),
            verdict=Verdict.from_dict(d.get("verdict", {}) or {}),
            root_cause=RootCause.from_dict(d.get("root_cause", {}) or {}),
            score_breakdown=ScoreBreakdown.from_dict(d.get("score_breakdown", {}) or {}),
            revision=d.get("revision"),
            harness_fix=HarnessFix.from_dict(hf) if hf else None,
            playbook_delta=d.get("playbook_delta"),
            provenance=Provenance.from_dict(d.get("provenance", {}) or {}),
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, text: str) -> TeachingPacket:
        return cls.from_dict(json.loads(text))


# --------------------------------------------------------------------------- #
# Playbook delta (§4.3)                                                        #
# --------------------------------------------------------------------------- #


@dataclass
class PlaybookDelta:
    """A typed ACE delta appended to the per-language playbook (§4.3)."""

    delta_id: str
    trajectory_id: str
    verdict: str  # "fail" | "partial" | "success"
    root_cause_class: str
    trigger: str
    observation: str
    rule: str
    evidence_trajectory: str
    language: str
    created: str = ""
    provenance: Provenance = field(default_factory=Provenance)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["provenance"] = self.provenance.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PlaybookDelta:
        return cls(
            delta_id=d.get("delta_id", ""),
            trajectory_id=d.get("trajectory_id", ""),
            verdict=d.get("verdict", ""),
            root_cause_class=d.get("root_cause_class", ""),
            trigger=d.get("trigger", ""),
            observation=d.get("observation", ""),
            rule=d.get("rule", ""),
            evidence_trajectory=d.get("evidence_trajectory", ""),
            language=d.get("language", ""),
            created=d.get("created", ""),
            provenance=Provenance.from_dict(d.get("provenance", {}) or {}),
        )


__all__ = [
    "TaskSource",
    "Layer",
    "VerdictLabel",
    "OracleStrength",
    "Task",
    "ModelInfo",
    "Step",
    "TestResults",
    "Verdict",
    "Trajectory",
    "RootCause",
    "ScoreBreakdown",
    "HarnessFix",
    "Provenance",
    "TeachingPacket",
    "PlaybookDelta",
]
