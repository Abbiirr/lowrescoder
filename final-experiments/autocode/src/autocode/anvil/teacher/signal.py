"""The execution-first signal hierarchy (Correction 4, made operational — §2).

The teacher scores in a strict order; LLM judgment only enters at the bottom, and
only where execution cannot decide:

    1. diff_applies?   ── deterministic (git apply)
    2. build_passed?   ── deterministic (compiler / interpreter)
    3. tests_pass?     ── deterministic; regressed>0 is an automatic FAIL
    4. lint + types?   ── deterministic
    ──────────────────── everything above is ground truth
    5. style/explanation ── LLM-judge (secondary; never gates promotion)

The load-bearing rule (§2): a teaching packet that emits a ``harness_fix`` /
``playbook_delta`` but whose verdict shows failed/regressed tests is **rejected
at the gate regardless of how good the judge scored the prose**. The judge only
ever adjusts a style sub-score.
"""

from __future__ import annotations

from autocode.anvil.teacher.schemas import (
    OracleStrength,
    ScoreBreakdown,
    Verdict,
    VerdictLabel,
)


def subscore_tests(verdict: Verdict) -> float:
    """Binary tests sub-score: 1.0 only if a real suite ran and was fully clean."""
    t = verdict.tests
    total = t.passed + t.failed
    if total == 0:
        return 0.0  # no executable test oracle decided this
    if t.failed == 0 and t.regressed == 0 and t.passed > 0:
        return 1.0
    return 0.0


def score_breakdown(verdict: Verdict, *, style_judge: float = 0.0) -> ScoreBreakdown:
    """Build the executable-first rubric. ``style_judge`` is the only soft signal."""
    return ScoreBreakdown(
        diff_applies=1.0 if verdict.diff_applies else 0.0,
        build=1.0 if verdict.build_passed else 0.0,
        tests=subscore_tests(verdict),
        lint=1.0 if verdict.lint_clean else 0.0,
        types=1.0 if verdict.types_clean else 0.0,
        style_judge=float(style_judge),
    )


def executable_gate(verdict: Verdict) -> bool:
    """The hard gate (§2): may a change derived from this verdict be promoted?

    True iff the diff applied, the build passed, and **no test failed or
    regressed**. Lint/types are quality signals, not promotion blockers here; the
    offline harness-fix path layers the additional ``no_regression_on`` edge
    guards on top via the patch-bundle gate.
    """
    if not verdict.diff_applies:
        return False
    if not verdict.build_passed:
        return False
    if verdict.tests.failed > 0 or verdict.tests.regressed > 0:
        return False
    return True


def primary_signal_is_decisive(verdict: Verdict) -> bool:
    """True when a real executable oracle (a test suite) decided the outcome.

    When False, the case is judge-weighted ``oracle_strength: weak`` and counts
    less in the eval corpus (§8.1).
    """
    return verdict.oracle_strength == OracleStrength.STRONG.value


def is_failure(verdict: Verdict) -> bool:
    """A run worth teaching from is anything that is not a clean success."""
    return verdict.label != VerdictLabel.SUCCESS.value


__all__ = [
    "subscore_tests",
    "score_breakdown",
    "executable_gate",
    "primary_signal_is_decisive",
    "is_failure",
]
