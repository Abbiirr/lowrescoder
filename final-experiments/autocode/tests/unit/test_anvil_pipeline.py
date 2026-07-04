"""Tests for the copycat patch-bundle pipeline: propose -> gate -> promote."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from autocode.anvil import paths
from autocode.anvil.census import Capability, Census
from autocode.anvil.gapdiff import Gap, GapReport
from autocode.anvil.gate import gate
from autocode.anvil.promote import PromoteError, promote
from autocode.anvil.propose import ProposeError, propose


def _census() -> Census:
    return Census(
        target="puku-cli",
        source="bundled snapshot (puku-cli --help)",
        capabilities=(
            Capability(id="flag:permission-mode", kind="flag", surface=("--permission-mode",)),
        ),
    )


def _report_with_gap() -> GapReport:
    cap = Capability(id="flag:permission-mode", kind="flag", surface=("--permission-mode",))
    return GapReport(
        target="puku-cli",
        gaps=(Gap(cap, "permissions", True, "gap"),),
    )


def _empty_report() -> GapReport:
    return GapReport(target="puku-cli")


def test_next_bundle_id_increments(tmp_path: Path) -> None:
    assert paths.next_bundle_id(tmp_path) == "pb_001"
    (paths.patch_bundles_dir(tmp_path) / "pb_001").mkdir(parents=True)
    (paths.patch_bundles_dir(tmp_path) / "pb_007").mkdir(parents=True)
    assert paths.next_bundle_id(tmp_path) == "pb_008"


def test_propose_writes_full_bundle(tmp_path: Path) -> None:
    bundle = propose(
        report=_empty_report(),
        census=_census(),
        capability_id="flag:permission-mode",
        root=tmp_path,
    )
    assert bundle.bundle_id == "pb_001"
    for name in (
        "decision.md",
        "proposal.md",
        "prediction_contract.yaml",
        "manifest_delta.yaml",
        "bundle.json",
    ):
        assert (bundle.path / name).is_file(), name
    meta = bundle.metadata()
    assert meta["capability_id"] == "flag:permission-mode"
    assert meta["manifest_entry"] == "cli.exec.permission_mode"
    assert meta["reuse_scope"] == "structure_only"
    assert meta["check_plan"]  # implemented capability has a real check plan
    # The decision records the clean-room discipline.
    decision = (bundle.path / "decision.md").read_text()
    assert "clean-room" in decision.lower()
    assert "no puku-cli source" in decision.lower() or "never vendored" in decision.lower()


def test_propose_marks_open_gap(tmp_path: Path) -> None:
    bundle = propose(
        report=_report_with_gap(),
        census=_census(),
        capability_id="flag:permission-mode",
        root=tmp_path,
    )
    assert bundle.is_open_gap is True
    assert bundle.metadata()["is_open_gap"] is True


def test_propose_unknown_capability_raises(tmp_path: Path) -> None:
    with pytest.raises(ProposeError, match="no clean-room proposal"):
        propose(
            report=_empty_report(),
            census=_census(),
            capability_id="flag:does-not-exist",
            root=tmp_path,
        )


def test_gate_pass_writes_reports(tmp_path: Path) -> None:
    bundle = propose(
        report=_empty_report(), census=_census(),
        capability_id="flag:permission-mode", root=tmp_path,
    )
    result = gate(bundle.path, runner=lambda plan, root: (0, "9 passed in 0.1s"))
    assert result.passed is True
    assert "9 passed" in result.summary
    score = json.loads((bundle.path / "prediction_score.json").read_text())
    assert score["met"] is True
    assert score["no_regression"] is True
    assert json.loads((bundle.path / "bundle.json").read_text())["status"] == "gated_pass"


def test_gate_fail_marks_not_met(tmp_path: Path) -> None:
    bundle = propose(
        report=_empty_report(), census=_census(),
        capability_id="flag:permission-mode", root=tmp_path,
    )
    result = gate(bundle.path, runner=lambda plan, root: (1, "1 failed, 3 passed"))
    assert result.passed is False
    assert json.loads((bundle.path / "prediction_score.json").read_text())["met"] is False


def test_gate_planned_capability_has_no_check_plan(tmp_path: Path) -> None:
    # A bundle with an empty check plan (a "planned", not-yet-implemented
    # capability) cannot pass the gate — there is no oracle to satisfy.
    bundle = propose(
        report=_empty_report(), census=_census(),
        capability_id="flag:permission-mode", root=tmp_path,
    )
    meta = json.loads((bundle.path / "bundle.json").read_text())
    meta["check_plan"] = []
    (bundle.path / "bundle.json").write_text(json.dumps(meta))

    # No runner needed: empty check plan -> automatically not passed.
    result = gate(bundle.path)
    assert result.passed is False
    assert "planned" in result.summary.lower()


def test_promote_requires_passing_gate(tmp_path: Path) -> None:
    bundle = propose(
        report=_empty_report(), census=_census(),
        capability_id="flag:permission-mode", root=tmp_path,
    )
    # Not gated yet.
    with pytest.raises(PromoteError, match="not been gated"):
        promote(bundle.path, root=tmp_path, timestamp="2026-06-21T00:00:00Z")
    # Gated but failing.
    gate(bundle.path, runner=lambda plan, root: (1, "1 failed"))
    with pytest.raises(PromoteError, match="prediction not met"):
        promote(bundle.path, root=tmp_path, timestamp="2026-06-21T00:00:00Z")


def test_promote_appends_audit_log(tmp_path: Path) -> None:
    bundle = propose(
        report=_empty_report(), census=_census(),
        capability_id="flag:permission-mode", root=tmp_path,
    )
    gate(bundle.path, runner=lambda plan, root: (0, "9 passed"))
    entry = promote(bundle.path, root=tmp_path, timestamp="2026-06-21T12:00:00Z")
    assert entry["capability_id"] == "flag:permission-mode"
    assert entry["reuse_scope"] == "structure_only"
    assert entry["promoted_on"] == "2026-06-21T12:00:00Z"

    log = paths.audit_log_path(tmp_path)
    assert log.is_file()
    lines = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
    assert len(lines) == 1
    assert lines[0]["bundle_id"] == "pb_001"
    assert json.loads((bundle.path / "bundle.json").read_text())["status"] == "promoted"


# ---------------------------------------------------------------------------
# Tier-0 0a — the edge-cost guard must be able to BLOCK a promotion.
# ---------------------------------------------------------------------------


def _regressing_verdict():
    """A verdict where tests pass but L4 share regresses (+400%)."""
    from autocode.anvil.teacher.cost import EdgeCost, compare

    baseline = EdgeCost(0.10, 1.0, 100.0, sample_count=10)
    candidate = EdgeCost(0.50, 1.0, 100.0, sample_count=10)
    return compare(baseline, candidate)


def _clean_verdict():
    """A verdict with no regression (baseline == candidate)."""
    from autocode.anvil.teacher.cost import EdgeCost, compare

    same = EdgeCost(0.10, 1.0, 100.0, sample_count=10)
    return compare(same, same)


def test_promote_refuses_edge_cost_regression(tmp_path: Path) -> None:
    """A bundle whose tests pass but whose edge cost regresses is refused (0a)."""
    bundle = propose(
        report=_empty_report(), census=_census(),
        capability_id="flag:permission-mode", root=tmp_path,
    )
    # Tests pass, but the edge-cost verdict regresses -> no_regression is False.
    result = gate(
        bundle.path,
        runner=lambda plan, root: (0, "9 passed"),
        edge_cost_verdict=_regressing_verdict(),
    )
    assert result.passed is True
    score = json.loads((bundle.path / "prediction_score.json").read_text())
    assert score["met"] is True
    assert score["no_regression"] is False

    with pytest.raises(PromoteError, match="edge-cost regression"):
        promote(bundle.path, root=tmp_path, timestamp="2026-06-23T00:00:00Z")
    # And nothing was written to the audit log.
    assert not paths.audit_log_path(tmp_path).is_file()


def test_promote_allows_measured_no_regression_and_records_flag(tmp_path: Path) -> None:
    """A measured, no-regression bundle promotes and the log says so honestly."""
    bundle = propose(
        report=_empty_report(), census=_census(),
        capability_id="flag:permission-mode", root=tmp_path,
    )
    gate(
        bundle.path,
        runner=lambda plan, root: (0, "9 passed"),
        edge_cost_verdict=_clean_verdict(),
    )
    entry = promote(bundle.path, root=tmp_path, timestamp="2026-06-23T01:00:00Z")
    assert entry["eval"] == {"met": True, "no_regression": True, "edge_cost_measured": True}


def test_promote_unmeasured_records_edge_cost_measured_false(tmp_path: Path) -> None:
    """A structural bundle gated without trajectory data still promotes, but the
    audit log records edge_cost_measured: False — no false 'no regression' stamp."""
    bundle = propose(
        report=_empty_report(), census=_census(),
        capability_id="flag:permission-mode", root=tmp_path,
    )
    gate(bundle.path, runner=lambda plan, root: (0, "9 passed"))  # no verdict
    entry = promote(bundle.path, root=tmp_path, timestamp="2026-06-23T02:00:00Z")
    assert entry["eval"]["met"] is True
    assert entry["eval"]["no_regression"] is True  # legacy/structural pass
    assert entry["eval"]["edge_cost_measured"] is False


# ---------------------------------------------------------------------------
# Tier-0 0c — gate-component lockout ("the single most important rule", 07 §7.2).
# A patch bundle that targets the verifier / eval suite / metrics / registry /
# kill switches / the gate itself is outside Anvil's action space and must fail
# the run — the loop can never be allowed to weaken its own oracle.
# ---------------------------------------------------------------------------


def _bundle_targeting(tmp_path: Path, manifest_entry: str, *, target: str = "puku-cli") -> Path:
    """Write a minimal, passing bundle whose manifest_entry/target we control."""
    bundle = propose(
        report=_empty_report(), census=_census(),
        capability_id="flag:permission-mode", root=tmp_path,
    )
    meta = json.loads((bundle.path / "bundle.json").read_text())
    meta["manifest_entry"] = manifest_entry
    meta["target"] = target
    (bundle.path / "bundle.json").write_text(json.dumps(meta))
    return bundle.path


@pytest.mark.parametrize(
    "manifest_entry",
    [
        "verifier",
        "teacher/verifier.py",
        "anvil.gate",
        "anvil.registry",
        "eval_suite",
        "prediction_metrics",
        "kill_switches",
    ],
)
def test_gate_refuses_bundle_targeting_gate_component(
    tmp_path: Path, manifest_entry: str
) -> None:
    from autocode.anvil.gate import GateError

    bundle_path = _bundle_targeting(tmp_path, manifest_entry)
    with pytest.raises(GateError, match="gate component"):
        gate(bundle_path, runner=lambda plan, root: (0, "9 passed"))
    # The lockout fires before any check runs: no report is written.
    assert not (bundle_path / "prediction_score.json").is_file()


def test_promote_refuses_bundle_targeting_gate_component(tmp_path: Path) -> None:
    # A bundle scored by some other path can still never be promoted if it names
    # a gate component (defense in depth with the gate-time check).
    bundle_path = _bundle_targeting(tmp_path, "cli.exec.add_dir")
    gate(bundle_path, runner=lambda plan, root: (0, "9 passed"))
    # Now rewrite the manifest_entry to a gate component after gating.
    meta = json.loads((bundle_path / "bundle.json").read_text())
    meta["manifest_entry"] = "anvil.registry"
    (bundle_path / "bundle.json").write_text(json.dumps(meta))
    with pytest.raises(PromoteError, match="gate component"):
        promote(bundle_path, root=tmp_path, timestamp="2026-06-23T03:00:00Z")
    assert not paths.audit_log_path(tmp_path).is_file()


def test_gate_allows_non_gate_component_target(tmp_path: Path) -> None:
    # Sanity: a normal capability target ("evaluate" contains "eval" only as a
    # fragment, not a whole word) passes the lockout cleanly.
    bundle_path = _bundle_targeting(tmp_path, "cli.exec.evaluate_run")
    result = gate(bundle_path, runner=lambda plan, root: (0, "9 passed"))
    assert result.passed is True
