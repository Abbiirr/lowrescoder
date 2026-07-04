"""Multi-objective promotion gate for the AutoCode eval flywheel.

This module operationalises the evaluation contract that the harness self-improvement
plans (``lowrescoder/new_plans/harness_copy_teacher/08_EVALUATION_AND_VERIFICATION.md``
§8.2/§8.3 and ``04_ARCHITECTURE.md`` §4.5) make normative. It answers one question that
``benchmark_runner.py`` deliberately does not: *given a baseline run and a candidate run
of the same eval corpus, should the candidate be promoted?*

The plan's rule is a vector with hard guards, not a single number:

    A patch is an improvement IFF
      * pass_at_1 rises on the held-out, STRONG-oracle set by more than the measured
        noise band,                                                  (primary quality)
      * regressions_introduced == 0,                                 (hard gate)
      * no edge guard regresses past tolerance:
          - layer_distribution.L4 must not increase  (escalating more is a regression),
          - latency_p50 / latency_p95 <= baseline + eps,
          - tokens_per_task           <= baseline + eps,
          - cost_usd_per_task         <= baseline,
      * the gain is NOT carried by weak-oracle cases alone.

Statistical rigor (§8.3): each case runs k times; we report mean +/- spread, compare
baseline vs candidate paired on the same case ids/seeds, measure the run-to-run noise
band from a baseline-vs-baseline comparison, and track both pass@k (capability) and
pass^k (reliability).

The module is pure / network-free so it can be unit-tested without a gateway. It consumes
either normalised :class:`CaseResult` records or the JSON reports emitted by
``benchmark_runner.save_run_report`` (via :func:`corpus_run_from_report`).
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

# A corpus run is k replicate results per case, keyed by case id.
CorpusRun = dict[str, "list[CaseResult]"]

STRONG = "strong"
WEAK = "weak"
HELD_OUT = "held_out"
DEV = "dev"


# --------------------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------------------
@dataclass
class CaseResult:
    """One replicate of one eval case.

    ``passed`` is the verifier verdict for this replicate (strong oracle => test-backed,
    weak oracle => reference-diff similarity). ``regressed`` is True when the diff made a
    previously-passing test fail (the §8.2 hard gate counts these). ``layer_l4_fraction``
    is the fraction of the trajectory's steps that ran at L4 — the edge-native guard
    metric from trajectory record §4.2.1; ``None`` means the harness did not record it.
    """

    case_id: str
    passed: bool
    oracle_strength: str = STRONG  # strong | weak
    split: str = HELD_OUT  # held_out | dev
    layer_l4_fraction: float | None = None
    latency_s: float = 0.0
    tokens: int = 0
    cost_usd: float = 0.0
    regressed: bool = False
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.oracle_strength not in (STRONG, WEAK):
            raise ValueError(f"oracle_strength must be {STRONG!r} or {WEAK!r}, got {self.oracle_strength!r}")
        if self.split not in (HELD_OUT, DEV):
            raise ValueError(f"split must be {HELD_OUT!r} or {DEV!r}, got {self.split!r}")


@dataclass
class Tolerances:
    """Edge-guard tolerances. Defaults encode 'no meaningful regression allowed'."""

    l4_abs: float = 0.0  # L4 fraction may rise by at most this (absolute)
    latency_rel: float = 0.05  # p50/p95 may rise by at most 5%
    tokens_rel: float = 0.05  # tokens/task may rise by at most 5%
    cost_abs: float = 0.0  # cost/task may rise by at most this (USD); local should be ~0
    # The held-out strong-oracle pass@1 improvement must exceed max(noise_band, min_effect).
    min_effect: float = 0.0


@dataclass
class MetricsVector:
    """The §8.2 multi-objective metric, computed over a chosen subset of a CorpusRun."""

    pass_at_1: float  # mean per-rep pass probability (capability, single sample)
    pass_caret_k: float  # fraction of cases solved in ALL k reps (reliability)
    pass_at_k: float  # fraction of cases solved in AT LEAST ONE rep
    regressions_introduced: int  # cases with any regressed replicate (hard gate)
    layer_l4_mean: float | None  # mean L4 fraction; None if unrecorded for all cases
    layer_l4_measured: bool
    latency_p50: float
    latency_p95: float
    tokens_per_task: float
    cost_usd_per_task: float
    n_cases: int
    n_strong: int
    n_weak: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "pass_at_1": round(self.pass_at_1, 6),
            "pass_caret_k": round(self.pass_caret_k, 6),
            "pass_at_k": round(self.pass_at_k, 6),
            "regressions_introduced": self.regressions_introduced,
            "layer_l4_mean": None if self.layer_l4_mean is None else round(self.layer_l4_mean, 6),
            "layer_l4_measured": self.layer_l4_measured,
            "latency_p50": round(self.latency_p50, 6),
            "latency_p95": round(self.latency_p95, 6),
            "tokens_per_task": round(self.tokens_per_task, 6),
            "cost_usd_per_task": round(self.cost_usd_per_task, 6),
            "n_cases": self.n_cases,
            "n_strong": self.n_strong,
            "n_weak": self.n_weak,
        }


@dataclass
class GuardResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class PromotionDecision:
    promote: bool
    reasons: list[str] = field(default_factory=list)
    guards: list[GuardResult] = field(default_factory=list)
    baseline: MetricsVector | None = None
    candidate: MetricsVector | None = None
    pass_at_1_delta: float = 0.0
    noise_band: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "promote": self.promote,
            "reasons": self.reasons,
            "guards": [{"name": g.name, "passed": g.passed, "detail": g.detail} for g in self.guards],
            "pass_at_1_delta": round(self.pass_at_1_delta, 6),
            "noise_band": round(self.noise_band, 6),
            "baseline": self.baseline.to_dict() if self.baseline else None,
            "candidate": self.candidate.to_dict() if self.candidate else None,
        }


# --------------------------------------------------------------------------------------
# Small statistics helpers (pure python, no numpy)
# --------------------------------------------------------------------------------------
def mean(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0


def stdev(values: Iterable[float]) -> float:
    vals = list(values)
    if len(vals) < 2:
        return 0.0
    mu = mean(vals)
    return math.sqrt(sum((v - mu) ** 2 for v in vals) / (len(vals) - 1))


def percentile(values: Iterable[float], pct: float) -> float:
    """Linear-interpolation percentile (pct in [0, 100]). Empty -> 0.0."""
    vals = sorted(values)
    if not vals:
        return 0.0
    if len(vals) == 1:
        return float(vals[0])
    rank = (pct / 100.0) * (len(vals) - 1)
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return float(vals[lo])
    frac = rank - lo
    return float(vals[lo] * (1 - frac) + vals[hi] * frac)


def pass_at_k(reps: list[CaseResult]) -> bool:
    """Capability: solved in at least one of k replicates."""
    return any(r.passed for r in reps)


def pass_caret_k(reps: list[CaseResult]) -> bool:
    """Reliability: solved in every one of k replicates (the SlopCodeBench concern)."""
    return bool(reps) and all(r.passed for r in reps)


def per_rep_pass_rate(reps: list[CaseResult]) -> float:
    """Empirical single-sample pass probability for one case (the pass@1 estimator)."""
    return mean(1.0 if r.passed for r in reps) if reps else 0.0  # placeholder, replaced below
