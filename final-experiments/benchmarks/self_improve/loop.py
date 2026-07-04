#!/usr/bin/env python
"""One self-improvement cycle: run a lane -> diagnose -> (auto-apply a fix) -> keep/revert.

Cron-driven. `python loop.py --once` does exactly one cycle and exits, guarded
by an flock so overlapping cron ticks never collide.

Cycle:
  health-gate gateway -> pick next lane (round-robin) -> run a small slice via
  the existing benchmark_runner -> classify each task (RESOLVED / INFRA_FAIL /
  FAIL) -> if a real FAIL exists and SELF_EDIT is on: snapshot the harness, drive
  `autocode exec` to write a minimal fix (rooted in autocode/, scope-locked to
  src/autocode/), re-run the same slice, KEEP only if a failing task now passes
  with zero regression of previously-passing tasks, else REVERT.
"""
from __future__ import annotations

import fcntl
import json
import subprocess
import sys
from pathlib import Path

import common as c

INFRA_HINTS = (
    "401", "403", "429", "502", "503", "rate limit", "rate-limit",
    "timeout", "connection refused", "connection error", "auth",
    "unauthorized", "overloaded",
)


def classify(task: dict) -> str:
    if task.get("resolved"):
        return "RESOLVED"
    ft = str(task.get("artifacts", {}).get("failure_type", "")).upper()
    if "INFRA" in ft:
        return "INFRA_FAIL"
    blob = json.dumps(task.get("artifacts", {})).lower()
    if any(h in blob for h in INFRA_HINTS):
        return "INFRA_FAIL"
    return "FAIL"


def per_task(result: dict) -> dict:
    return {t["task_id"]: classify(t) for t in result.get("results", [])}


def pick_lane() -> str:
    i = 0
    if c.CURSOR.exists():
        i = json.loads(c.CURSOR.read_text()).get("i", 0)
    lane = c.LANES[i % len(c.LANES)]
    c.CURSOR.write_text(json.dumps({"i": (i + 1) % len(c.LANES)}))
    return lane


def run_lane(lane: str, model: str, run_id: str) -> dict | None:
    cmd = [
        c.UV, "run", "python", str(c.RUNNER), "--agent", "autocode",
        "--lane", lane, "--model", model, "--max-tasks", str(c.MAX_TASKS),
        "--task-timeout-s", str(c.TASK_TIMEOUT_S), "--run-id", run_id,
    ]
    try:
        subprocess.run(
            cmd, cwd=c.AUTOCODE_DIR, env=c.agent_env(model),
            timeout=c.RUN_TIMEOUT_S, capture_output=True, text=True,
        )
    except subprocess.TimeoutExpired:
        return None
    return load_result(lane, run_id)


def load_result(lane: str, run_id: str) -> dict | None:
    cands = sorted(
        c.RESULTS_DIR.glob(f"*-{lane}-autocode.json"),
        key=lambda p: p.stat().st_mtime, reverse=True,
    )
    for p in cands[:12]:
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        if d.get("contract", {}).get("run_id") == run_id:
            return d
    return None


def trace_for(task_id: str) -> str:
    dirs = sorted(
        c.SANDBOXES.glob(f"bench_*_{task_id}_*"),
        key=lambda p: p.stat().st_mtime, reverse=True,
    )
    if not dirs:
        return ""
    d = dirs[0]
    parts = []
    for name in ("grading_attempt_1.txt", "grading_attempt_2.txt", "agent.log"):
        f = d / name
        if f.exists():
            parts.append(f"--- {name} ---\n{f.read_text()[-1800:]}")
    return "\n".join(parts)[-4000:]


def propose_fix(failed_ids: list[str]) -> bool:
    traces = "\n\n".join(f"### {t}\n{trace_for(t)}" for t in failed_ids[:2])
    goal = c.goal_text()
    prompt = (
        (f"{goal}\n\n---\n\n" if goal else "")
        + "Benchmark tasks failed for a harness reason (not a model fluke). "
        "Diagnose the failure class from the traces below and make the smallest "
        "edit under src/autocode/ that moves us toward the goal above. "
        "Read before you edit.\n\n"
        f"{traces}"
    )
    cmd = [
        c.UV, "run", "autocode", "exec", prompt,
        "--cd", str(c.AUTOCODE_DIR),
        "--permission-mode", "acceptEdits",
        "--output-format", "text",
        "--max-budget-usd", str(c.PROPOSE_BUDGET_USD),
        "--append-system-prompt", c.SCOPE_LOCK,
    ]
    try:
        r = subprocess.run(
            cmd, cwd=c.AUTOCODE_DIR, env=c.agent_env(c.PROPOSE_MODEL),
            timeout=c.PROPOSE_TIMEOUT_S, capture_output=True, text=True,
        )
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def cycle() -> None:
    lane = pick_lane()

    if lane == "B30-TBENCH" and not c.TB_READY.exists():
        c.append_ledger({"event": "skip", "lane": lane, "reason": "tb_not_ready"})
        c.render_status()
        return
    if not c.gateway_healthy():
        c.append_ledger({"event": "skip", "lane": lane, "reason": "gateway_unhealthy"})
        c.render_status()
        return

    run_id = f"selfimprove-{c.now()}"
    base = run_lane(lane, c.RUN_MODEL, run_id)
    if base is None:
        c.append_ledger({"event": "run_error", "lane": lane, "run_id": run_id})
        c.render_status()
        return

    base_map = per_task(base)
    real_fails = [t for t, v in base_map.items() if v == "FAIL"]
    # all counts from one source (our classifier) so the ledger trend is consistent
    row = {
        "event": "run", "lane": lane, "run_id": run_id,
        "resolved": sum(1 for v in base_map.values() if v == "RESOLVED"),
        "total": len(base_map),
        "infra_fails": sum(1 for v in base_map.values() if v == "INFRA_FAIL"),
        "real_fails": len(real_fails),
    }

    if c.SELF_EDIT and real_fails:
        snap = c.snapshot_harness()
        ok = propose_fix(real_fails)
        changed = c.changed_files(snap)
        if not ok or not changed:
            c.restore_harness(snap)
            row["self_edit"] = "no_change"
        elif not c.py_syntax_ok(changed):
            c.restore_harness(snap)
            row["self_edit"] = "syntax_revert"
        else:
            ver = run_lane(lane, c.RUN_MODEL, f"{run_id}-verify")
            if ver is None:
                c.restore_harness(snap)
                row["self_edit"] = "verify_error_revert"
            else:
                vmap = per_task(ver)
                regressed = [t for t in base_map
                             if base_map[t] == "RESOLVED" and vmap.get(t) != "RESOLVED"]
                newpass = [t for t in real_fails if vmap.get(t) == "RESOLVED"]
                if regressed or not newpass:
                    c.restore_harness(snap)
                    row["self_edit"] = f"revert(reg={len(regressed)},new={len(newpass)})"
                else:
                    row["self_edit"] = f"KEEP(+{len(newpass)})"
                    row["kept_files"] = [str(p.relative_to(c.HARNESS_SRC)) for p in changed]
                    row["snapshot"] = str(snap)  # for manual rollback

    c.append_ledger(row)
    c.render_status()


def main() -> int:
    once = "--once" in sys.argv
    c.STATE.mkdir(parents=True, exist_ok=True)
    lock = open(c.LOCK, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("another cycle is running; skipping", file=sys.stderr)
        return 0
    try:
        while True:
            try:
                cycle()
            except Exception as exc:
                c.append_ledger({"event": "crash", "error": str(exc)})
                c.render_status()
                import time; time.sleep(60)  # brief pause after crash before retrying
            if once:
                break
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
