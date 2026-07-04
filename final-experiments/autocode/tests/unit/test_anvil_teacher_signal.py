"""Tests for the execution-first signal hierarchy (§2)."""

from __future__ import annotations

from autocode.anvil.teacher.schemas import (
    OracleStrength,
    TestResults,
    Verdict,
    VerdictLabel,
)
from autocode.anvil.teacher.signal import (
    executable_gate,
    is_failure,
    primary_signal_is_decisive,
    score_breakdown,
    subscore_tests,
)


def _verdict(**kw) -> Verdict:
    base = dict(
        diff_applies=True,
        build_passed=True,
        tests=TestResults(passed=10),
        lint_clean=True,
        types_clean=True,
        label=VerdictLabel.SUCCESS.value,
        oracle_strength=OracleStrength.STRONG.value,
    )
    base.update(kw)
    return Verdict(**base)


def test_subscore_tests_binary() -> None:
    assert subscore_tests(_verdict(tests=TestResults(passed=10))) == 1.0
    assert subscore_tests(_verdict(tests=TestResults(passed=9, failed=1))) == 0.0
    assert subscore_tests(_verdict(tests=TestResults(passed=10, regressed=1))) == 0.0
    assert subscore_tests(_verdict(tests=TestResults())) == 0.0  # no oracle


def test_score_breakdown_executable_first() -> None:
    v = _verdict(lint_clean=False, tests=TestResults(passed=10))
    sb = score_breakdown(v, style_judge=0.9)
    assert sb.diff_applies == 1.0
    assert sb.build == 1.0
    assert sb.tests == 1.0
    assert sb.lint == 0.0
    assert sb.style_judge == 0.9  # secondary, carried but not gating


def test_executable_gate_rejects_failed_tests_regardless_of_judge() -> None:
    # The load-bearing rule: failing tests => no promotion, even with a great judge score.
    v = _verdict(tests=TestResults(passed=8, failed=3), label=VerdictLabel.FAIL.value)
    sb = score_breakdown(v, style_judge=1.0)
    assert sb.style_judge == 1.0
    assert executable_gate(v) is False


def test_executable_gate_rejects_regressions() -> None:
    v = _verdict(tests=TestResults(passed=10, regressed=1), label=VerdictLabel.FAIL.value)
    assert executable_gate(v) is False


def test_executable_gate_rejects_unappliable_diff() -> None:
    v = _verdict(diff_applies=False, label=VerdictLabel.ERROR.value)
    assert executable_gate(v) is False


def test_executable_gate_passes_clean_run() -> None:
    assert executable_gate(_verdict()) is True


def test_partial_passes_gate_but_is_a_failure_to_teach_from() -> None:
    # Lint dirty but tests green: gate allows promotion, yet it's still worth teaching.
    v = _verdict(lint_clean=False, label=VerdictLabel.PARTIAL.value)
    assert executable_gate(v) is True
    assert is_failure(v) is True


def test_primary_signal_decisive_tracks_oracle_strength() -> None:
    assert primary_signal_is_decisive(_verdict(oracle_strength=OracleStrength.STRONG.value))
    assert not primary_signal_is_decisive(_verdict(oracle_strength=OracleStrength.WEAK.value))
