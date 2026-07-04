"""Tests for the ``autocode anvil`` command surface (copycat manual MVP)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from autocode.anvil.census import Capability, Census
from autocode.cli import app

runner = CliRunner()

REGISTRY = """\
targets:
  - id: puku-cli
    channel: [structural]
    source: "puku-cli --help"
    license: "review-before-use"
    reuse_scope: structure_only
    notes: "test"
"""


def _seed_anvil(tmp_path: Path, *, with_census: bool = False) -> Path:
    root = tmp_path / "anvil"
    (root / "copycat").mkdir(parents=True)
    (root / "copycat" / "registry.yaml").write_text(REGISTRY)
    if with_census:
        census = Census(
            target="puku-cli",
            source="bundled snapshot (puku-cli --help)",
            target_version="1.8.27",
            capabilities=(
                Capability(id="flag:permission-mode", kind="flag", surface=("--permission-mode",)),
                Capability(id="flag:effort", kind="flag", surface=("--effort",)),
                Capability(id="flag:json", kind="flag", surface=("--json",)),
            ),
        )
        census.write_yaml(root / "copycat" / "census" / "puku-cli.yaml")
    return root


def test_registry_lists_targets(tmp_path: Path) -> None:
    root = _seed_anvil(tmp_path)
    result = runner.invoke(app, ["anvil", "copycat", "registry", "--anvil-root", str(root)])
    assert result.exit_code == 0
    assert "puku-cli" in result.output
    assert "structure_only" in result.output


def test_census_unauthorized_target_is_refused(tmp_path: Path) -> None:
    root = _seed_anvil(tmp_path)
    result = runner.invoke(
        app, ["anvil", "copycat", "census", "claude-code", "--anvil-root", str(root)]
    )
    assert result.exit_code == 2
    assert "not in the registry" in result.output.lower() or "refused" in result.output.lower()


def test_census_writes_file(tmp_path: Path) -> None:
    root = _seed_anvil(tmp_path)
    fake = Census(
        target="puku-cli", source="bundled snapshot (puku-cli --help)",
        capabilities=(Capability(id="flag:effort", kind="flag", surface=("--effort",)),),
    )
    with patch("autocode.anvil.cli.anvil_targets.collect_census", return_value=fake):
        result = runner.invoke(
            app, ["anvil", "copycat", "census", "puku-cli", "--anvil-root", str(root)]
        )
    assert result.exit_code == 0
    assert (root / "copycat" / "census" / "puku-cli.yaml").is_file()
    assert "1" in result.output  # 1 capability


def test_gap_diff_reports_gaps(tmp_path: Path) -> None:
    root = _seed_anvil(tmp_path, with_census=True)
    result = runner.invoke(
        app, ["anvil", "copycat", "gap-diff", "puku-cli", "--anvil-root", str(root)]
    )
    assert result.exit_code == 0
    # effort is a real gap; permission-mode now landed (present); json present.
    assert "flag:effort" in result.output


def test_gap_diff_json(tmp_path: Path) -> None:
    root = _seed_anvil(tmp_path, with_census=True)
    result = runner.invoke(
        app, ["anvil", "copycat", "gap-diff", "puku-cli", "--anvil-root", str(root), "--json"]
    )
    assert result.exit_code == 0
    assert '"target"' in result.output
    assert '"gaps"' in result.output


def test_propose_gate_promote_end_to_end(tmp_path: Path) -> None:
    root = _seed_anvil(tmp_path, with_census=True)

    # propose a clean-room capability that is actually implemented in AutoCode.
    res_propose = runner.invoke(
        app,
        ["anvil", "copycat", "propose", "puku-cli", "flag:permission-mode",
         "--anvil-root", str(root)],
    )
    assert res_propose.exit_code == 0, res_propose.output
    assert "pb_001" in res_propose.output
    assert (root / "patch_bundles" / "pb_001" / "decision.md").is_file()

    # gate with an injected passing check-runner (no real pytest spawn here).
    with patch("autocode.anvil.cli.gate") as gate_mock:
        from autocode.anvil.gate import gate as real_gate

        gate_mock.side_effect = lambda bundle_dir, **kw: real_gate(
            bundle_dir, runner=lambda plan, repo: (0, "tests passed")
        )
        res_gate = runner.invoke(
            app, ["anvil", "gate", "pb_001", "--anvil-root", str(root)]
        )
    assert res_gate.exit_code == 0, res_gate.output
    assert "PASS" in res_gate.output

    # promote records the audit entry.
    res_promote = runner.invoke(
        app, ["anvil", "promote", "pb_001", "--anvil-root", str(root)]
    )
    assert res_promote.exit_code == 0, res_promote.output
    assert "Promoted" in res_promote.output
    audit = root / "audit_log.jsonl"
    assert audit.is_file()
    assert "flag:permission-mode" in audit.read_text()


def _write_trajectories(
    path: Path, *, n: int = 2, l4_steps: int = 0, wall_s: float = 1.0,
    tokens: int = 100, n_steps: int = 4,
) -> None:
    """Write a small trajectory-store JSONL the edge-cost measurer can read."""
    from autocode.anvil.teacher.schemas import (
        Layer,
        Step,
        Task,
        Trajectory,
        Verdict,
        VerdictLabel,
    )

    lines = []
    for k in range(n):
        steps = [
            Step(
                i=i,
                layer=Layer.L4.value if i < l4_steps else Layer.L1.value,
                tokens={"in": tokens // n_steps, "out": 0},
                latency_ms=int(wall_s * 1000 / n_steps),
            )
            for i in range(n_steps)
        ]
        tj = Trajectory(
            trajectory_id=f"t{k}",
            task=Task(instruction="x"),
            steps=steps,
            outcome=Verdict(label=VerdictLabel.FAIL.value),
            cost={"usd": 0.0, "wall_s": wall_s},
        )
        lines.append(json.dumps(tj.to_dict()))
    path.write_text("\n".join(lines) + "\n")


def test_gate_edge_cost_requires_both_trajectory_options(tmp_path: Path) -> None:
    """Passing only one of the two trajectory stores is refused (exit 2)."""
    root = _seed_anvil(tmp_path, with_census=True)
    runner.invoke(
        app, ["anvil", "copycat", "propose", "puku-cli", "flag:permission-mode",
              "--anvil-root", str(root)],
    )
    res = runner.invoke(
        app, ["anvil", "gate", "pb_001", "--anvil-root", str(root),
              "--baseline-trajectories", str(tmp_path / "b.jsonl")],
    )
    assert res.exit_code == 2
    assert "BOTH" in res.output


def test_gate_measures_edge_cost_from_trajectories(tmp_path: Path) -> None:
    """The gate CLI loads trajectory stores, measures, and folds the verdict
    into the prediction score (Tier-0 0a wiring)."""
    root = _seed_anvil(tmp_path, with_census=True)
    runner.invoke(
        app, ["anvil", "copycat", "propose", "puku-cli", "flag:permission-mode",
              "--anvil-root", str(root)],
    )
    base = tmp_path / "baseline.jsonl"
    cand = tmp_path / "candidate.jsonl"
    _write_trajectories(base, l4_steps=0)
    _write_trajectories(cand, l4_steps=0)  # identical -> no regression

    with patch("autocode.anvil.cli.gate") as gate_mock:
        from autocode.anvil.gate import gate as real_gate

        # Forward the CLI-computed edge_cost_verdict into a tests-pass gate run.
        gate_mock.side_effect = lambda bundle_dir, **kw: real_gate(
            bundle_dir, runner=lambda plan, repo: (0, "tests passed"), **kw
        )
        res = runner.invoke(
            app, ["anvil", "gate", "pb_001", "--anvil-root", str(root),
                  "--baseline-trajectories", str(base),
                  "--candidate-trajectories", str(cand)],
        )
    assert res.exit_code == 0, res.output
    assert "no regression" in res.output
    score = json.loads(
        (root / "patch_bundles" / "pb_001" / "prediction_score.json").read_text()
    )
    assert score["edge_cost_measured"] is True
    assert score["no_regression"] is True
