"""Edge-cost measurement (PLAN_04 §0.3.5, §0.3.6, §3.2, §7 Phase 3 line 462).

The three prediction-contract guards — ``layer_distribution.L4``,
``latency_p50``, ``tokens_per_task`` — are *mandatory* (PLAN_05 §0.3.6 design
constraint 6). Until now they were hard-coded string constants at
``gate.py:99``, ``propose.py:220`` and ``loop.py:226``: the contract asserted
"no regression" without actually measuring it.

This module turns the three guards into measured quantities derived from a
population of :class:`~autocode.anvil.teacher.schemas.Trajectory`:

* ``layer_distribution.L4`` — the mean fraction of steps that ran at the L4
  (cloud / fallback) layer. Lower is better; an L4 spike means the harness lost
  deterministic coverage.
* ``latency_p50`` — the median wall-clock seconds per task
  (``Trajectory.cost["wall_s"]``).
* ``tokens_per_task`` — the mean tokens (prompt + completion) per task,
  summed across all steps.

A contract :class:`compare` enforces no-regression within a per-guard relative
tolerance (default +5% for L4 share, +10% for latency and tokens). A candidate
whose any guard exceeds ``baseline × (1 + tol)`` fails the edge-cost contract,
regardless of whether its tests pass.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

from autocode.anvil.teacher.schemas import Layer, Trajectory

# The three mandatory guard names — the same strings gate.py / propose.py /
# loop.py already embed in `no_regression_on`. Centralised here so a rename
# updates every call site at once.
GUARD_LAYER_L4 = "layer_distribution.L4"
GUARD_LATENCY_P50 = "latency_p50"
GUARD_TOKENS_PER_TASK = "tokens_per_task"
ALL_GUARDS: tuple[str, ...] = (GUARD_LAYER_L4, GUARD_LATENCY_P50, GUARD_TOKENS_PER_TASK)


class EdgeCostError(Exception):
    """Edge-cost measurement was refused (insufficient data, malformed input)."""


@dataclass(frozen=True)
class Tolerances:
    """Per-guard relative regression tolerance (fraction; 0.05 = +5%).

    L4 share is held to a tighter band than latency/tokens because an L4 spike
    is a deterministic-coverage regression — the harness silently lost a tier-1
    tool — and should be caught even when token/latency noise hides it.
    """

    layer_distribution_L4: float = 0.05  # noqa: N815 - matches the guard string
    latency_p50: float = 0.10
    tokens_per_task: float = 0.10

    def for_guard(self, guard: str) -> float:
        return {
            GUARD_LAYER_L4: self.layer_distribution_L4,
            GUARD_LATENCY_P50: self.latency_p50,
            GUARD_TOKENS_PER_TASK: self.tokens_per_task,
        }[guard]


@dataclass(frozen=True)
class EdgeCost:
    """The measured values of the three guards on one trajectory population."""

    layer_distribution_L4: float  # noqa: N815 - matches the guard string
    latency_p50: float  # noqa: N815
    tokens_per_task: float
    sample_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def value_for(self, guard: str) -> float:
        return {
            GUARD_LAYER_L4: self.layer_distribution_L4,
            GUARD_LATENCY_P50: self.latency_p50,
            GUARD_TOKENS_PER_TASK: self.tokens_per_task,
        }[guard]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EdgeCost:
        return cls(
            layer_distribution_L4=float(d.get("layer_distribution_L4", 0.0)),  # noqa: N815
            latency_p50=float(d.get("latency_p50", 0.0)),
            tokens_per_task=float(d.get("tokens_per_task", 0.0)),
            sample_count=int(d.get("sample_count", 0)),
        )


def _tokens_in_trajectory(tj: Trajectory) -> int:
    return sum(s.tokens.get("in", 0) + s.tokens.get("out", 0) for s in tj.steps)


def _l4_fraction(tj: Trajectory) -> float:
    """Fraction of steps at L4. Falls back to ``layer_distribution[L4]`` if no steps."""
    if tj.steps:
        n_l4 = sum(1 for s in tj.steps if s.layer == Layer.L4.value)
        return n_l4 / len(tj.steps)
    return float(tj.layer_distribution.get(Layer.L4.value, 0.0))


def measure(trajectories: Sequence[Trajectory]) -> EdgeCost:
    """Compute the three guards over a non-empty trajectory population.

    Raises :class:`EdgeCostError` on empty input — there is no meaningful
    "median latency" over zero tasks.
    """
    if not trajectories:
        raise EdgeCostError("cannot measure edge cost on an empty trajectory set")
    l4 = statistics.fmean(_l4_fraction(tj) for tj in trajectories)
    wall = [float(tj.cost.get("wall_s", 0.0)) for tj in trajectories]
    latency_p50 = statistics.median(wall)
    tokens = statistics.fmean(_tokens_in_trajectory(tj) for tj in trajectories)
    return EdgeCost(
        layer_distribution_L4=round(l4, 6),
        latency_p50=round(latency_p50, 6),
        tokens_per_task=round(tokens, 6),
        sample_count=len(trajectories),
    )


@dataclass(frozen=True)
class GuardVerdict:
    """One guard's measured comparison."""

    guard: str
    baseline: float
    candidate: float
    threshold: float  # baseline * (1 + tol)
    no_regression: bool
    relative_delta: float  # (candidate - baseline) / baseline; +ve = worse

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EdgeCostVerdict:
    """The full edge-cost comparison across all guards."""

    overall_no_regression: bool
    tolerances: Tolerances
    guards: tuple[GuardVerdict, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_no_regression": self.overall_no_regression,
            "tolerances": asdict(self.tolerances),
            "guards": [g.to_dict() for g in self.guards],
        }

    def verdict_for(self, guard: str) -> GuardVerdict | None:
        return next((g for g in self.guards if g.guard == guard), None)


def _relative_delta(baseline: float, candidate: float) -> float:
    if baseline <= 0:
        # Baseline of zero is "free" — any positive candidate is +inf regression.
        # Treat it as 0.0 if candidate is also 0, else a large sentinel.
        return 0.0 if candidate <= 0 else float("inf")
    return (candidate - baseline) / baseline


def compare(
    baseline: EdgeCost,
    candidate: EdgeCost,
    *,
    tolerances: Tolerances | None = None,
) -> EdgeCostVerdict:
    """Compare a candidate against a baseline under per-guard tolerances.

    A guard regresses iff ``candidate > baseline × (1 + tol)``. The overall
    verdict is the conjunction across all three guards.
    """
    tols = tolerances or Tolerances()
    verdicts: list[GuardVerdict] = []
    for guard in ALL_GUARDS:
        b = baseline.value_for(guard)
        c = candidate.value_for(guard)
        threshold = b * (1 + tols.for_guard(guard))
        rel = _relative_delta(b, c)
        verdicts.append(
            GuardVerdict(
                guard=guard,
                baseline=round(b, 6),
                candidate=round(c, 6),
                threshold=round(threshold, 6),
                no_regression=c <= threshold,
                relative_delta=round(rel, 6) if rel != float("inf") else rel,
            )
        )
    overall = all(v.no_regression for v in verdicts)
    return EdgeCostVerdict(
        overall_no_regression=overall,
        tolerances=tols,
        guards=tuple(verdicts),
    )


def measure_many_populations(
    populations: dict[str, Sequence[Trajectory]],
) -> dict[str, EdgeCost]:
    """Convenience: measure several named populations at once."""
    return {name: measure(trajs) for name, trajs in populations.items() if trajs}


def trajectories_from_jsonl(path: Any) -> list[Trajectory]:
    """Read a trajectory-store JSONL file (one Trajectory per line)."""
    from pathlib import Path

    p = Path(path)
    if not p.is_file():
        raise EdgeCostError(f"trajectory store not found: {p}")
    out: list[Trajectory] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(Trajectory.from_dict(__import__("json").loads(line)))
    return out


_ = Iterable  # re-exported for type hints elsewhere if needed
