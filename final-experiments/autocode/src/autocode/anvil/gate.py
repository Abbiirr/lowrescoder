"""Apply a patch bundle's scoped checks and score its prediction (PLAN_05 §6).

``gate`` runs the bundle's ``check_plan`` (its executable oracle) and writes
``eval_report.json`` + ``prediction_score.json``. A bundle whose checks fail —
or that has no check plan yet (a *planned* capability) — does not pass the gate
and therefore cannot be promoted.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autocode.anvil import paths
from autocode.anvil.registry import GateComponentError, assert_not_gate_component

# (check_plan, repo_root) -> (returncode, captured_output)
CheckRunner = Callable[[list[str], Path], tuple[int, str]]


class GateError(Exception):
    """The bundle could not be gated (missing/invalid bundle)."""


@dataclass(frozen=True)
class GateResult:
    bundle_id: str
    passed: bool
    command: str
    returncode: int
    summary: str
    eval_report_path: Path
    prediction_score_path: Path


def _default_check_runner(
    check_plan: list[str],
    repo_root: Path,
    *,
    command: tuple[str, ...] = ("uv", "run", "pytest"),
) -> tuple[int, str]:
    """Default check runner.

    The command prefix is configurable (cross-cutting X.2): set
    ``AUTOCODE_ANVIL_CHECK_RUNNER`` to a space-separated command (e.g.
    ``"pytest -x"`` or ``"poetry run pytest"``) to override the default
    ``uv run pytest``. Tests pass an injected ``runner`` instead.
    """
    import os

    env_cmd = os.environ.get("AUTOCODE_ANVIL_CHECK_RUNNER", "").strip()
    if env_cmd:
        cmd = env_cmd.split() + [*check_plan, "-q"]
    else:
        cmd = [*command, *check_plan, "-q"]
    proc = subprocess.run(  # noqa: S603 - fixed launcher, bundle-derived test paths
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=900,
    )
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or ""))[-4000:]


def _summary_line(output: str) -> str:
    for line in reversed(output.splitlines()):
        if line.strip():
            return line.strip()
    return ""


def gate(
    bundle_dir: str | Path,
    *,
    repo_root: Path | None = None,
    runner: CheckRunner | None = None,
    edge_cost_verdict: Any | None = None,
) -> GateResult:
    """Apply a bundle's check plan and score its prediction.

    ``edge_cost_verdict`` (optional) is an
    :class:`autocode.anvil.teacher.cost.EdgeCostVerdict` produced by measuring
    the candidate's three mandatory guards against a baseline. When supplied,
    ``prediction_score.no_regression`` is the conjunction of the test pass and
    the edge-cost verdict — a candidate whose tests pass but regresses any guard
    fails the contract (PLAN_04 §0.3.6). When omitted, the score falls back to
    "tests-passed == no-regression" for backwards compatibility, with an
    explicit ``edge_cost_measured: False`` flag in the score.
    """
    bundle_dir = Path(bundle_dir)
    meta_path = bundle_dir / "bundle.json"
    if not meta_path.is_file():
        raise GateError(f"not a patch bundle (no bundle.json): {bundle_dir}")
    meta: dict[str, Any] = json.loads(meta_path.read_text(encoding="utf-8"))

    # Gate-component lockout (07 §7.2, "the single most important rule"): a patch
    # bundle that targets the verifier / eval suite / metrics / registry / kill
    # switches / the gate itself is outside Anvil's action space and fails the run
    # *before* any check runs. Raised as GateError so the CLI surfaces it uniformly.
    try:
        assert_not_gate_component(meta.get("manifest_entry"), meta.get("target"))
    except GateComponentError as exc:
        raise GateError(str(exc)) from exc

    check_plan: list[str] = list(meta.get("check_plan", []) or [])
    repo = repo_root or paths._PACKAGE_ROOT

    if not check_plan:
        passed = False
        returncode = 1
        command = "(none)"
        summary = "no check plan — capability is planned, not implemented"
    else:
        run = runner or _default_check_runner
        returncode, output = run(check_plan, repo)
        passed = returncode == 0
        command = "pytest " + " ".join(check_plan)
        summary = _summary_line(output)

    # Edge-cost: if a verdict is supplied, fold it into no_regression.
    ec_measured = edge_cost_verdict is not None
    ec_no_regression = True
    if ec_measured:
        ec_no_regression = bool(getattr(edge_cost_verdict, "overall_no_regression", True))
    no_regression = passed and ec_no_regression

    eval_report = {
        "bundle_id": meta.get("bundle_id"),
        "command": command,
        "check_plan": check_plan,
        "returncode": returncode,
        "passed": passed,
        "summary": summary,
    }
    prediction_score = {
        "capability": meta.get("manifest_entry"),
        "met": passed,
        # The mandatory edge-cost guards: when measured, the conjunction with
        # the test result is enforced; when not measured, the score degrades to
        # the test-only assertion for backwards compatibility and records it.
        "no_regression": no_regression,
        "no_regression_on": ["layer_distribution.L4", "latency_p50", "tokens_per_task"],
        "edge_cost_measured": ec_measured,
        "edge_cost_no_regression": ec_no_regression,
        "returncode": returncode,
    }
    if ec_measured:
        ec_dict = getattr(edge_cost_verdict, "to_dict", None)
        if callable(ec_dict):
            prediction_score["edge_cost_verdict"] = ec_dict()

    eval_path = bundle_dir / "eval_report.json"
    score_path = bundle_dir / "prediction_score.json"
    eval_path.write_text(json.dumps(eval_report, indent=2) + "\n", encoding="utf-8")
    score_path.write_text(json.dumps(prediction_score, indent=2) + "\n", encoding="utf-8")

    meta["status"] = "gated_pass" if passed else "gated_fail"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    return GateResult(
        bundle_id=str(meta.get("bundle_id")),
        passed=passed,
        command=command,
        returncode=returncode,
        summary=summary,
        eval_report_path=eval_path,
        prediction_score_path=score_path,
    )
