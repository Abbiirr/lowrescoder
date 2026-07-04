"""Live harness calibration runner — produces the harness trustworthiness report.

This is the "use a known-good control to test the test" runner. It:

1. Runs the synthetic oracles (golden / noop / wrong) on each calibration task and checks
   each against its known-correct verdict (false-positive / false-negative detection).
2. Runs the real control agent (puku-cli, via the gateway) on each task N times, measuring
   whether a known-good agent passes solvable tasks and how stable the verdict is across
   repetitions (verdict-flip rate — the pass^k stability signal).
3. Writes a Markdown calibration report + a JSON summary.

Usage (from superproject root, with gateway env loaded):

    set -a; . ./.env; set +a
    uv run python benchmarks/calibrate_harness.py --reps 3
    uv run python benchmarks/calibrate_harness.py --oracles-only   # skip live agent

The oracle invariants are also covered by ``benchmarks/tests/test_harness_calibration.py``
(network-free, hard-asserted in CI); this runner adds the live-agent dimension and the
human-readable report.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import shutil
import statistics
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow `python benchmarks/calibrate_harness.py` (script mode) as well as `-m`.
_SUPERPROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_SUPERPROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_SUPERPROJECT_ROOT))

from benchmarks.adapters.base import BudgetProfile  # noqa: E402
from benchmarks.adapters.oracle_adapters import (  # noqa: E402
    GoldenOracle,
    NoopOracle,
    WrongOracle,
)
from benchmarks.adapters.puku_adapter import PukuAdapter  # noqa: E402
from benchmarks.calibration_tasks import (  # noqa: E402
    CALIBRATION_TASKS,
    CalibrationTask,
)

_REPORT_DIR = Path(__file__).resolve().parent / "docs"
_REPORT_MD = _REPORT_DIR / "harness-calibration-report.md"
_REPORT_JSON = _REPORT_DIR / "harness-calibration-report.json"

_ORACLE_BUDGET = BudgetProfile(wall_time_s=120, token_cap=1000, max_tool_calls=1)
_AGENT_BUDGET = BudgetProfile(wall_time_s=240, token_cap=50_000, max_tool_calls=40)


def _load_dotenv(root: Path) -> None:
    """Best-effort .env loader so gateway creds are present when run standalone."""
    import os

    env_path = root / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


def _is_bookkeeping(rel: str) -> bool:
    """Generated artifacts (e.g. pytest caches) that are not real agent edits."""
    return (
        rel.endswith((".pyc", ".pyo"))
        or "__pycache__/" in rel or rel.startswith("__pycache__/")
        or ".pytest_cache/" in rel or rel.startswith(".pytest_cache/")
        or rel.startswith(".git/") or "/.git/" in rel
    )


def _sandbox_signature(work_dir: Path) -> dict[str, str]:
    """Content hash of every source file under work_dir — used to detect agent edits.

    Excludes grading-generated bookkeeping (pytest caches, .pyc) so the 'edited?' signal
    reflects real source changes, not side effects of running the grading command.
    """
    sig: dict[str, str] = {}
    for p in sorted(work_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(work_dir))
        if _is_bookkeeping(rel):
            continue
        try:
            sig[rel] = hashlib.sha256(p.read_bytes()).hexdigest()[:12]
        except Exception:
            sig[rel] = "?"
    return sig


def _independent_grade(task: CalibrationTask, sandbox: Path) -> bool | None:
    """Re-run the task's grading command independently. None if no grading command."""
    if not task.grading_command:
        return None
    try:
        r = subprocess.run(
            task.grading_command, shell=True, cwd=str(sandbox),
            capture_output=True, text=True, timeout=120,
        )
        return r.returncode == 0
    except Exception:
        return None


@dataclass
class RepRecord:
    resolved: bool
    duration_s: float = 0.0
    changed: bool = False              # did the agent modify the sandbox?
    regrade: bool | None = None        # independent re-grade verdict on a FAIL
    num_turns: Any = None
    error: str = ""


@dataclass
class ProbeResult:
    label: str
    kind: str                          # "oracle" | "agent"
    expected_resolved: bool
    reps_data: list[RepRecord] = field(default_factory=list)

    @property
    def verdicts(self) -> list[bool]:
        return [r.resolved for r in self.reps_data]

    @property
    def reps(self) -> int:
        return len(self.reps_data)

    @property
    def pass_rate(self) -> float:
        return sum(self.verdicts) / self.reps if self.reps else 0.0

    @property
    def flips(self) -> int:
        if not self.reps_data:
            return 0
        majority = sum(self.verdicts) >= (self.reps / 2)
        return sum(1 for v in self.verdicts if v != majority)

    @property
    def correct(self) -> bool:
        return self.reps > 0 and all(v == self.expected_resolved for v in self.verdicts)


async def _run_probe(
    adapter, task: CalibrationTask, expected: bool, reps: int, label: str, kind: str,
) -> ProbeResult:
    pr = ProbeResult(label=label, kind=kind, expected_resolved=expected)
    bt = task.to_benchmark_task()
    budget = _AGENT_BUDGET if kind == "agent" else _ORACLE_BUDGET
    for _ in range(reps):
        sandbox = task.make_sandbox()
        before = _sandbox_signature(sandbox)
        rec = RepRecord(resolved=False)
        try:
            res = await adapter.solve_task(bt, sandbox, budget)
            rec.resolved = bool(res.resolved)
            rec.duration_s = res.wall_time_s
            rec.num_turns = (res.artifacts or {}).get("puku_num_turns")
            rec.error = (res.error or "")[:300]
            rec.changed = _sandbox_signature(sandbox) != before
            # If the agent was graded FAIL, independently re-grade to tell a real harness
            # false-negative (correct work scored FAIL) apart from a genuine agent miss.
            if kind == "agent" and not rec.resolved:
                rec.regrade = _independent_grade(task, sandbox)
        except Exception as e:  # noqa: BLE001
            rec.error = f"{type(e).__name__}: {e}"
        finally:
            shutil.rmtree(sandbox, ignore_errors=True)
        pr.reps_data.append(rec)
    return pr


async def calibrate(reps: int, oracles_only: bool) -> dict[str, Any]:
    per_task: list[dict[str, Any]] = []
    # Grader-trustworthiness counters (oracles + proven false negatives from the agent).
    oracle_false_pos = 0       # noop/wrong oracle graded PASS
    oracle_false_neg = 0       # golden oracle graded FAIL
    harness_false_neg = 0      # agent produced a correct fix but was graded FAIL (proven via re-grade)
    # Agent-capability counters (NOT harness defects).
    agent_miss = 0             # agent graded FAIL and re-grade confirms it did not solve
    agent_flip_rates: list[float] = []
    agent_solves = 0
    agent_runs = 0

    for task in CALIBRATION_TASKS:
        probes: list[ProbeResult] = [
            await _run_probe(GoldenOracle(), task, True, 1, "oracle-golden", "oracle"),
            await _run_probe(NoopOracle(), task, False, 1, "oracle-noop", "oracle"),
            await _run_probe(WrongOracle(), task, False, 1, "oracle-wrong", "oracle"),
        ]
        if not oracles_only:
            probes.append(await _run_probe(PukuAdapter(), task, True, reps, "puku", "agent"))

        for pr in probes:
            if pr.kind == "oracle":
                for r in pr.reps_data:
                    if pr.expected_resolved and not r.resolved:
                        oracle_false_neg += 1
                    if (not pr.expected_resolved) and r.resolved:
                        oracle_false_pos += 1
            else:  # agent
                agent_flip_rates.append(pr.flips / pr.reps if pr.reps else 0.0)
                for r in pr.reps_data:
                    agent_runs += 1
                    if r.resolved:
                        agent_solves += 1
                    elif r.regrade is True:
                        harness_false_neg += 1   # correct work scored FAIL → real harness bug
                    else:
                        agent_miss += 1          # agent genuinely did not solve

        per_task.append({
            "task_id": task.task_id,
            "category": task.category,
            "probes": [
                {
                    "label": pr.label,
                    "kind": pr.kind,
                    "expected_resolved": pr.expected_resolved,
                    "verdicts": pr.verdicts,
                    "pass_rate": round(pr.pass_rate, 3),
                    "flips": pr.flips,
                    "correct": pr.correct,
                    "reps": [
                        {
                            "resolved": r.resolved,
                            "changed": r.changed,
                            "regrade_on_fail": r.regrade,
                            "num_turns": r.num_turns,
                            "duration_s": r.duration_s,
                            "error": r.error,
                        }
                        for r in pr.reps_data
                    ],
                }
                for pr in probes
            ],
        })

    trustworthy = oracle_false_pos == 0 and oracle_false_neg == 0 and harness_false_neg == 0
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reps": reps,
        "oracles_only": oracles_only,
        "summary": {
            "tasks": len(CALIBRATION_TASKS),
            # Grader correctness (what makes the harness trustworthy):
            "oracle_false_positives": oracle_false_pos,
            "oracle_false_negatives": oracle_false_neg,
            "proven_harness_false_negatives": harness_false_neg,
            "harness_grading_trustworthy": trustworthy,
            # Agent capability/stability (informational, NOT a harness defect):
            "agent_runs": agent_runs,
            "agent_solves": agent_solves,
            "agent_solve_rate": round(agent_solves / agent_runs, 3) if agent_runs else None,
            "agent_misses": agent_miss,
            "agent_mean_flip_rate": (
                round(statistics.mean(agent_flip_rates), 3) if agent_flip_rates else None
            ),
        },
        "tasks": per_task,
    }


def _render_md(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Harness Calibration Report",
        "",
        f"> Generated: {report['generated_at']}",
        f"> Reps per live-agent probe: {report['reps']}"
        + ("  ·  oracles-only run" if report["oracles_only"] else ""),
        "",
        "Calibrates the evaluation harness against known-good controls. Two questions are",
        "kept strictly separate:",
        "",
        "1. **Is the grader trustworthy?** — measured by synthetic oracles (deterministic",
        "   ground truth) plus any *proven* false negative (a real agent producing a correct",
        "   fix that the grader still scored FAIL, confirmed by an independent re-grade).",
        "2. **How capable/stable is the agent?** — puku-cli's solve rate and verdict-flip",
        "   rate. An agent that simply fails to solve a task is **not** a harness defect.",
        "",
        "## Verdict — grader trustworthiness",
        "",
        f"- **Harness grading trustworthy:** "
        f"{'✅ YES' if s['harness_grading_trustworthy'] else '❌ NO'}",
        f"- Oracle false positives (wrong/empty graded PASS): **{s['oracle_false_positives']}**",
        f"- Oracle false negatives (golden graded FAIL): **{s['oracle_false_negatives']}**",
        f"- Proven harness false negatives (agent correct but graded FAIL): "
        f"**{s['proven_harness_false_negatives']}**",
        "",
        "## Agent control (puku-cli) — capability & stability",
        "",
        f"- Solve rate: **{s['agent_solve_rate']}** "
        f"({s['agent_solves']}/{s['agent_runs']} runs)"
        + ("" if s["agent_runs"] else "  _(no live run)_"),
        f"- Agent misses (genuinely unsolved, re-grade confirms): **{s['agent_misses']}**",
        f"- Mean verdict-flip rate (instability): **{s['agent_mean_flip_rate']}**",
        "",
        "## Per-task probes",
        "",
        "| Task | Probe | Expected | Verdicts | Correct | Flips | turns | edited? |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for t in report["tasks"]:
        for p in t["probes"]:
            exp = "PASS" if p["expected_resolved"] else "FAIL"
            verdicts = ",".join("P" if v else "F" for v in p["verdicts"])
            ok = "✅" if p["correct"] else ("—" if p["kind"] == "agent" else "❌")
            turns = ",".join(str(r["num_turns"]) for r in p["reps"] if r["num_turns"] is not None) or "-"
            edited = ",".join("y" if r["changed"] else "n" for r in p["reps"])
            lines.append(
                f"| {t['task_id']} | {p['label']} | {exp} | {verdicts} | {ok} | "
                f"{p['flips']} | {turns} | {edited} |"
            )
    lines += [
        "",
        "## Interpretation",
        "",
        "- The **Correct** column applies to oracles (deterministic ground truth). For the",
        "  `puku` agent rows it is shown as `—`: a puku FAIL is only a harness problem if",
        "  `regrade_on_fail` is `true` in the JSON (counted under *proven harness false",
        "  negatives*); otherwise it is an agent miss, visible as `edited?=n` (no edits) or a",
        "  wrong edit.",
        "- **Tokens/cost:** puku self-reports 0 through the gateway's OpenAI provider; honest",
        "  token/cost accounting must be sourced from the gateway (LiteLLM), not the agent.",
        "- Oracle invariants are also enforced as hard-asserted unit tests in",
        "  `benchmarks/tests/test_harness_calibration.py`.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Harness calibration runner")
    parser.add_argument("--reps", type=int, default=3, help="live-agent reps per task")
    parser.add_argument("--oracles-only", action="store_true", help="skip the live agent")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parent.parent
    _load_dotenv(root)

    report = asyncio.run(calibrate(args.reps, args.oracles_only))

    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
    _REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _REPORT_MD.write_text(_render_md(report), encoding="utf-8")

    s = report["summary"]
    print(json.dumps(s, indent=2))
    print(f"\nReport: {_REPORT_MD}")
    return 0 if s["harness_grading_trustworthy"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
