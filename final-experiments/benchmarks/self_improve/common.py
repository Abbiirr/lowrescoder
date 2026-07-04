"""Shared helpers for the autocode self-improving benchmark loop.

Cron-driven, no daemon: one `loop.py --once` per tick runs a single cycle and
exits; `heartbeat.py` is the read-only watchdog. State lives under ./state.

Safety rails (apply even in auto-apply mode, because the tree is not git):
  1. snapshot_harness() before any self-edit  -> revertible without git
  2. propose runs with `autocode exec --cd autocode/` so the agent is rooted in
     the harness package and physically cannot reach benchmarks/ or graders
  3. changed_files() + the validate re-run gate keeps an edit only if a real
     FAIL becomes RESOLVED with no previously-passing task regressing
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# --- Paths -----------------------------------------------------------------
ROOT = Path("/home/bs01763/projects/ai/autocode-full")
AUTOCODE_DIR = ROOT / "autocode"
HARNESS_SRC = AUTOCODE_DIR / "src" / "autocode"   # only edits here are kept
RUNNER = ROOT / "benchmarks" / "benchmark_runner.py"
RESULTS_DIR = ROOT / "docs" / "qa" / "test-results"
SANDBOXES = ROOT / "sandboxes"

STATE = Path(__file__).resolve().parent / "state"
LEDGER = STATE / "ledger.jsonl"
STATUS = STATE / "STATUS.md"
BACKUPS = STATE / "backups"
CURSOR = STATE / "cursor.json"
LOCK = STATE / "loop.lock"
TB_READY = STATE / "tb_ready"          # touch this once terminal-bench works
GOAL = STATE.parent / "GOAL.md"        # objective injected into every self-edit

# --- Config (env-overridable) ----------------------------------------------
GATEWAY = os.environ.get("AUTOCODE_LLM_API_BASE", "http://localhost:4000/v1")
GATEWAY_HEALTH = GATEWAY.rsplit("/v1", 1)[0] + "/health/readiness"
KEY = os.environ.get("LITELLM_API_KEY", "sk-my-secret-gateway-key")

# Cron has a minimal PATH; resolve uv to an absolute path so subprocess finds it.
LOCAL_BIN = str(Path.home() / ".local" / "bin")
UV = shutil.which("uv") or f"{LOCAL_BIN}/uv"

# One lane per cycle, round-robin. B30-TBENCH skips fast until TB_READY exists.
LANES = os.environ.get(
    "SI_LANES", "SMOKE,META,B9-PROXY,B11,B13-PROXY,B30-TBENCH"
).split(",")
RUN_MODEL = os.environ.get("SI_MODEL", "bench_stable")
PROPOSE_MODEL = os.environ.get("SI_PROPOSE_MODEL", "coding")
MAX_TASKS = int(os.environ.get("SI_MAX_TASKS", "4"))
# Per-task cap so slow lanes (B9-PROXY/B7/B8 have 24h lane budgets) can't hang
# the whole cycle and starve the hourly cadence. 0 = use the lane budget.
TASK_TIMEOUT_S = int(os.environ.get("SI_TASK_TIMEOUT_S", "600"))
SELF_EDIT = os.environ.get("SI_SELF_EDIT", "1") == "1"   # auto-apply validated fixes
PROPOSE_BUDGET_USD = float(os.environ.get("SI_PROPOSE_BUDGET_USD", "0.50"))
RUN_TIMEOUT_S = int(os.environ.get("SI_RUN_TIMEOUT_S", "7200"))
PROPOSE_TIMEOUT_S = int(os.environ.get("SI_PROPOSE_TIMEOUT_S", "1200"))

SCOPE_LOCK = (
    "SELF-IMPROVEMENT TASK. You are editing the autocode harness itself. "
    "Edit ONLY files under src/autocode/. Do NOT touch tests, benchmarks, "
    "fixtures, graders, or any verify/grading script — changing how success is "
    "measured is forbidden and will be reverted. Make the SMALLEST change that "
    "fixes the described failure class. Do not add dependencies."
)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def goal_text() -> str:
    return GOAL.read_text() if GOAL.exists() else ""


def agent_env(model: str | None = None) -> dict:
    """Env that forces the gateway and drops the broken upstream OLLAMA_HOST."""
    e = dict(os.environ)
    e.update({
        "AUTOCODE_LLM_PROVIDER": "openrouter",
        "AUTOCODE_LLM_API_BASE": GATEWAY,
        "OPENROUTER_API_KEY": KEY,
        "LITELLM_API_KEY": KEY,
        "LITELLM_MASTER_KEY": KEY,
    })
    if model:
        e["AUTOCODE_MODEL"] = model
    e.pop("OLLAMA_HOST", None)  # shell default points at a dead host
    e["PATH"] = LOCAL_BIN + ":" + e.get("PATH", "/usr/bin:/bin")  # cron-safe
    return e


def gateway_healthy(timeout: int = 8) -> bool:
    try:
        with urllib.request.urlopen(GATEWAY_HEALTH, timeout=timeout) as r:
            return "healthy" in r.read().decode("utf-8", "replace")
    except Exception:
        return False


# --- Ledger ----------------------------------------------------------------
def append_ledger(row: dict) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as f:
        f.write(json.dumps({"ts": utc_iso(), **row}) + "\n")


def read_ledger(limit: int = 500) -> list[dict]:
    if not LEDGER.exists():
        return []
    rows = [json.loads(x) for x in LEDGER.read_text().splitlines() if x.strip()]
    return rows[-limit:]


# --- Harness snapshot / revert (no git, so copy the tree) ------------------
def snapshot_harness() -> Path:
    BACKUPS.mkdir(parents=True, exist_ok=True)
    dest = BACKUPS / now()
    # ponytail: ignore venv/cache so the copy is the source, not the world.
    shutil.copytree(
        HARNESS_SRC, dest,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"),
    )
    return dest


def restore_harness(snap: Path) -> None:
    """Full replace of src/autocode from a snapshot — simplest correct revert."""
    shutil.rmtree(HARNESS_SRC)
    shutil.copytree(snap, HARNESS_SRC)


def changed_files(snap: Path) -> list[Path]:
    """Files under HARNESS_SRC added or modified vs the snapshot."""
    out: list[Path] = []
    for p in HARNESS_SRC.rglob("*"):
        if not p.is_file() or "__pycache__" in p.parts:
            continue
        b = snap / p.relative_to(HARNESS_SRC)
        if not b.exists() or b.read_bytes() != p.read_bytes():
            out.append(p)
    return out


def py_syntax_ok(files: list[Path]) -> bool:
    for p in files:
        if p.suffix == ".py":
            r = subprocess.run(
                [sys.executable, "-m", "py_compile", str(p)],
                capture_output=True, text=True,
            )
            if r.returncode != 0:
                return False
    return True


# --- Status render (shared by loop + heartbeat) ----------------------------
def render_status() -> None:
    rows = read_ledger()
    runs = [r for r in rows if r.get("event") == "run"]
    keeps = [r for r in runs if str(r.get("self_edit", "")).startswith("KEEP")]
    last = rows[-1] if rows else {}

    # latest resolved-rate per lane
    by_lane: dict[str, dict] = {}
    for r in runs:
        by_lane[r["lane"]] = r  # last wins

    lines = ["# autocode self-improving loop — STATUS", ""]
    lines.append(f"_updated {utc_iso()}  ·  gateway {'UP' if gateway_healthy() else 'DOWN'}_")
    lines.append("")
    lines.append(f"- cycles run: **{len(runs)}**   ·   kept harness improvements: **{len(keeps)}**")
    if last:
        lines.append(f"- last event: `{last.get('event')}` on `{last.get('lane','-')}` at {last.get('ts')}")
    lines.append("")
    lines.append("## latest per lane")
    lines.append("| lane | resolved | infra_fail | real_fail | last self-edit |")
    lines.append("|------|----------|-----------|-----------|----------------|")
    for lane, r in by_lane.items():
        lines.append(
            f"| {lane} | {r.get('resolved','-')}/{r.get('total','-')} "
            f"| {r.get('infra_fails','-')} | {r.get('real_fails','-')} "
            f"| {r.get('self_edit','-')} |"
        )
    lines.append("")
    if keeps:
        lines.append("## kept improvements (auto-applied, live tree)")
        for k in keeps[-10:]:
            files = ", ".join(k.get("kept_files", [])) or "?"
            lines.append(f"- {k.get('ts')} · {k.get('lane')} · {k.get('self_edit')} · {files}")
        lines.append("")
    lines.append("## recent events")
    for r in rows[-12:]:
        lines.append(f"- `{r.get('ts')}` {r.get('event')} {r.get('lane','')} {r.get('reason') or r.get('self_edit') or ''}".rstrip())

    STATE.mkdir(parents=True, exist_ok=True)
    STATUS.write_text("\n".join(lines) + "\n")
