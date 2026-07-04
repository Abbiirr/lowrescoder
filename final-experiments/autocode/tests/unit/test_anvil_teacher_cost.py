"""Tests for PLAN_04 §7 Phase 3 — edge-cost measurement (teacher/cost.py).

Verifies the three mandatory prediction-contract guards
(``layer_distribution.L4``, ``latency_p50``, ``tokens_per_task``) are actually
measured from trajectory populations and enforced in the contract comparison
(no more hard-coded string assertions).
"""

from __future__ import annotations

import pytest

from autocode.anvil.teacher.cost import (
    ALL_GUARDS,
    GUARD_LATENCY_P50,
    GUARD_LAYER_L4,
    GUARD_TOKENS_PER_TASK,
    EdgeCost,
    EdgeCostError,
    Tolerances,
    compare,
    measure,
)
from autocode.anvil.teacher.schemas import (
    Layer,
    Step,
    Task,
    Trajectory,
    Verdict,
    VerdictLabel,
)


def _traj(
    *,
    l4_fraction: float = 0.0,
    wall_s: float = 1.0,
    tokens: int = 100,
    n_steps: int = 4,
    label: str = VerdictLabel.FAIL.value,
) -> Trajectory:
    """Build a minimal trajectory with controllable cost knobs."""
    n_l4 = round(n_steps * l4_fraction)
    per_step = tokens // n_steps
    last_step = tokens - per_step * (n_steps - 1)
    steps = [
        Step(
            i=i,
            layer=Layer.L4.value if i < n_l4 else Layer.L1.value,
            tokens={"in": (last_step if i == n_steps - 1 else per_step), "out": 0},
            latency_ms=int(wall_s * 1000 / n_steps),
        )
        for i in range(n_steps)
    ]
    return Trajectory(
        trajectory_id=f"t-{l4_fraction}-{wall_s}-{tokens}",
        task=Task(instruction="x"),
        steps=steps,
        outcome=Verdict(label=label),
        cost={"usd": 0.0, "wall_s": wall_s},
    )


def test_measure_returns_three_guards_with_sample_count() -> None:
    populations = [_traj(l4_fraction=0.25, wall_s=2.0, tokens=200) for _ in range(4)]
    ec = measure(populations)
    assert ec.sample_count == 4
    assert ec.layer_distribution_L4 == pytest.approx(0.25, abs=1e-6)
    assert ec.latency_p50 == pytest.approx(2.0, abs=1e-6)
    assert ec.tokens_per_task == pytest.approx(200.0, abs=1e-6)


def test_measure_empty_population_raises() -> None:
    with pytest.raises(EdgeCostError, match="empty"):
        measure([])


def test_measure_median_uses_median_not_mean() -> None:
    # Odd count, widely-spread wall times -> p50 is the median, not the mean.
    populations = [
        _traj(wall_s=1.0),
        _traj(wall_s=2.0),
        _traj(wall_s=100.0),
    ]
    ec = measure(populations)
    assert ec.latency_p50 == pytest.approx(2.0, abs=1e-6)


def test_measure_l4_falls_back_to_layer_distribution_dict() -> None:
    # Trajectory with no steps should fall back to the layer_distribution map.
    tj = Trajectory(
        trajectory_id="t-empty",
        task=Task(instruction="x"),
        steps=[],
        outcome=Verdict(label=VerdictLabel.FAIL.value),
        cost={"usd": 0.0, "wall_s": 1.0},
        layer_distribution={"L1": 0.0, "L2": 0.0, "L3": 0.0, "L4": 0.5},
    )
    ec = measure([tj])
    assert ec.layer_distribution_L4 == pytest.approx(0.5, abs=1e-6)


def test_all_guards_constant_lists_three_names_in_contract_order() -> None:
    assert ALL_GUARDS == (
        GUARD_LAYER_L4,
        GUARD_LATENCY_P50,
        GUARD_TOKENS_PER_TASK,
    )


# ---------------------------------------------------------------------------
# compare()
# ---------------------------------------------------------------------------


def test_compare_no_regression_when_candidate_within_tolerance() -> None:
    baseline = EdgeCost(0.10, 1.0, 100.0, sample_count=10)
    # +4% L4, +5% latency, +5% tokens — all inside the default tolerance.
    candidate = EdgeCost(0.104, 1.05, 105.0, sample_count=10)
    verdict = compare(baseline, candidate)
    assert verdict.overall_no_regression is True
    for guard in ALL_GUARDS:
        v = verdict.verdict_for(guard)
        assert v is not None
        assert v.no_regression is True


def test_compare_l4_regression_fails_contract() -> None:
    baseline = EdgeCost(0.10, 1.0, 100.0, sample_count=10)
    # +10% L4 — outside the +5% L4 tolerance; the harness lost deterministic coverage.
    candidate = EdgeCost(0.11, 1.0, 100.0, sample_count=10)
    verdict = compare(baseline, candidate)
    assert verdict.overall_no_regression is False
    assert verdict.verdict_for(GUARD_LAYER_L4) is not None
    assert verdict.verdict_for(GUARD_LAYER_L4).no_regression is False
    # Other guards are still fine.
    assert verdict.verdict_for(GUARD_LATENCY_P50).no_regression is True
    assert verdict.verdict_for(GUARD_TOKENS_PER_TASK).no_regression is True


def test_compare_latency_regression_fails_contract() -> None:
    baseline = EdgeCost(0.10, 1.0, 100.0, sample_count=10)
    candidate = EdgeCost(0.10, 1.20, 100.0, sample_count=10)  # +20% latency > +10% tol
    verdict = compare(baseline, candidate)
    assert verdict.overall_no_regression is False
    assert verdict.verdict_for(GUARD_LATENCY_P50).no_regression is False


def test_compare_tokens_regression_fails_contract() -> None:
    baseline = EdgeCost(0.10, 1.0, 100.0, sample_count=10)
    candidate = EdgeCost(0.10, 1.0, 120.0, sample_count=10)  # +20% tokens > +10% tol
    verdict = compare(baseline, candidate)
    assert verdict.overall_no_regression is False
    assert verdict.verdict_for(GUARD_TOKENS_PER_TASK).no_regression is False


def test_compare_custom_tolerances_widen_or_tighten_per_guard() -> None:
    baseline = EdgeCost(0.10, 1.0, 100.0, sample_count=10)
    candidate = EdgeCost(0.11, 1.0, 100.0, sample_count=10)  # +10% L4
    # With the default +5% L4 tolerance this fails; with +15% it passes.
    strict = compare(baseline, candidate)
    assert strict.overall_no_regression is False
    loose = compare(baseline, candidate, tolerances=Tolerances(layer_distribution_L4=0.15))
    assert loose.overall_no_regression is True


def test_compare_handles_zero_baseline() -> None:
    # Baseline of zero (the harness previously had no L4 escalation at all).
    baseline = EdgeCost(0.0, 0.0, 0.0, sample_count=10)
    # Candidate still zero -> no regression.
    same = compare(baseline, EdgeCost(0.0, 0.0, 0.0, sample_count=10))
    assert same.overall_no_regression is True
    # Candidate non-zero -> infinite relative regression on every guard.
    worse = compare(baseline, EdgeCost(0.1, 1.0, 100.0, sample_count=10))
    assert worse.overall_no_regression is False
    for guard in ALL_GUARDS:
        assert worse.verdict_for(guard).no_regression is False


def test_verdict_to_dict_round_trips() -> None:
    baseline = EdgeCost(0.10, 1.0, 100.0, sample_count=10)
    candidate = EdgeCost(0.11, 1.05, 105.0, sample_count=10)
    verdict = compare(baseline, candidate)
    d = verdict.to_dict()
    assert d["overall_no_regression"] is False  # L4 regressed
    assert len(d["guards"]) == 3
    guard_names = {g["guard"] for g in d["guards"]}
    assert guard_names == set(ALL_GUARDS)


# ---------------------------------------------------------------------------
# Integration with gate.py
# ---------------------------------------------------------------------------


def test_gate_folds_edge_cost_verdict_into_prediction_score(tmp_path) -> None:
    """When an edge_cost_verdict is supplied, gate() enforces it."""
    import json

    from autocode.anvil.census import Capability, Census
    from autocode.anvil.gapdiff import GapReport
    from autocode.anvil.gate import gate
    from autocode.anvil.propose import propose

    census = Census(
        target="puku-cli",
        source="test",
        capabilities=(Capability(id="flag:permission-mode", kind="flag", surface=("--x",)),),
    )
    bundle = propose(
        report=GapReport(target="puku-cli"),
        census=census,
        capability_id="flag:permission-mode",
        root=tmp_path,
    )

    # Tests pass but L4 regresses.
    baseline = EdgeCost(0.10, 1.0, 100.0, sample_count=10)
    candidate = EdgeCost(0.50, 1.0, 100.0, sample_count=10)  # +400% L4
    verdict = compare(baseline, candidate)

    result = gate(
        bundle.path,
        runner=lambda plan, root: (0, "1 passed"),
        edge_cost_verdict=verdict,
    )
    score = json.loads((bundle.path / "prediction_score.json").read_text())
    # Tests passed (met), but no_regression is False because L4 regressed.
    assert result.passed is True
    assert score["met"] is True
    assert score["no_regression"] is False
    assert score["edge_cost_measured"] is True
    assert score["edge_cost_no_regression"] is False
    assert "edge_cost_verdict" in score


def test_gate_without_edge_cost_verdict_is_backward_compatible(tmp_path) -> None:
    """Without edge_cost_verdict, gate() falls back to tests-only assertion."""
    import json

    from autocode.anvil.census import Capability, Census
    from autocode.anvil.gapdiff import GapReport
    from autocode.anvil.gate import gate
    from autocode.anvil.propose import propose

    census = Census(
        target="puku-cli",
        source="test",
        capabilities=(Capability(id="flag:permission-mode", kind="flag", surface=("--x",)),),
    )
    bundle = propose(
        report=GapReport(target="puku-cli"),
        census=census,
        capability_id="flag:permission-mode",
        root=tmp_path,
    )

    result = gate(bundle.path, runner=lambda plan, root: (0, "1 passed"))
    score = json.loads((bundle.path / "prediction_score.json").read_text())
    assert result.passed is True
    assert score["no_regression"] is True  # legacy behavior
    assert score["edge_cost_measured"] is False
    assert "edge_cost_verdict" not in score


def test_gate_default_runner_reads_env_for_command(tmp_path, monkeypatch) -> None:
    """The default check runner honors AUTOCODE_ANVIL_CHECK_RUNNER (cross-cutting X.2)."""
    from autocode.anvil import gate

    captured: dict[str, list[str]] = {}

    class _FakeProc:
        returncode = 0
        stdout = "1 passed"
        stderr = ""

    def fake_run(cmd, **kw):  # noqa: ANN001
        captured["cmd"] = list(cmd)
        return _FakeProc()

    monkeypatch.setattr(gate.subprocess, "run", fake_run)
    monkeypatch.setenv("AUTOCODE_ANVIL_CHECK_RUNNER", "poetry run pytest -x")

    # Build a bundle with a check plan and run via the default runner.
    from autocode.anvil.census import Capability, Census
    from autocode.anvil.gapdiff import GapReport
    from autocode.anvil.propose import propose

    census = Census(
        target="puku-cli",
        source="test",
        capabilities=(Capability(id="flag:permission-mode", kind="flag", surface=("--x",)),),
    )
    bundle = propose(
        report=GapReport(target="puku-cli"),
        census=census,
        capability_id="flag:permission-mode",
        root=tmp_path,
    )

    gate.gate(bundle.path)
    assert captured["cmd"][:4] == ["poetry", "run", "pytest", "-x"]
    # The check plan path is appended after the env-configured prefix.
    assert "tests/unit/test_permission_mode.py" in captured["cmd"]
