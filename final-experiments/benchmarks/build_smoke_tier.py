"""Generate the curated SMOKE-tier manifest (Phase 2, build step 2).

Promotes a small, balanced, self-contained set of existing fixture tasks into a single
``smoke-tier-subset.json`` so the harness has a fast (< ~10 min) pre-flight lane that spans
categories and languages. Selection is intentionally light (easy/medium, fixture-based with
``bash setup.sh``/``bash verify.sh``) and every task already runs through ``benchmark_runner``.

Run once to (re)generate the manifest:

    uv run python benchmarks/build_smoke_tier.py

Then run it via the SMOKE lane. Use the `fast` alias — it is ~4.5x faster than the `coding`
reasoning alias (measured 19s vs 86s on a simple task) and keeps the tier a true pre-flight:

    uv run python benchmarks/benchmark_runner.py --agent puku --lane SMOKE --model fast --task-timeout-s 150
"""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_DIR = _ROOT / "benchmarks" / "e2e" / "external"
OUT = MANIFEST_DIR / "smoke-tier-subset.json"

# (source manifest stem, task_id) — one per category/difficulty cell, balanced + light.
SMOKE_SELECTION: list[tuple[str, str]] = [
    ("b27-efficiency-subset", "b27-minimal-config-change"),   # bugfix · python · easy (verified)
    ("b24-security-subset", "b24-hardcoded-secrets"),         # security · python · easy
    ("b20-terminal-ops-subset", "b20-fix-broken-symlinks"),   # file_operations · bash · easy
    ("b28-repeatability-subset", "b28-deterministic-sort"),   # reliability · python · easy
    ("b21-regression-contract-subset", "b21-refactor-preserve-api"),  # refactoring · python · medium
    ("b18-heldout-prototype-subset", "b18-fix-date-parsing"), # bugfix(held-out) · python · medium
]


def _load_task(stem: str, task_id: str) -> dict:
    data = json.loads((MANIFEST_DIR / f"{stem}.json").read_text(encoding="utf-8"))
    for t in data.get("tasks", []):
        if t.get("task_id") == task_id:
            t = dict(t)
            t.setdefault("extra", {})
            if isinstance(t["extra"], dict):
                t["extra"]["smoke_source_manifest"] = stem
            return t
    raise KeyError(f"{task_id} not found in {stem}")


def build() -> dict:
    tasks = [_load_task(stem, tid) for stem, tid in SMOKE_SELECTION]
    return {
        "_meta": {
            "description": (
                "Curated SMOKE tier — a fast, balanced pre-flight slice across categories "
                "and languages, promoted from the prototype fixture lanes. Not a parity "
                "benchmark; use for quick harness/agent smoke checks."
            ),
            "comparison_validity": "internal",
            "selection": [f"{stem}:{tid}" for stem, tid in SMOKE_SELECTION],
            "tier": "smoke",
            "generated_by": "benchmarks/build_smoke_tier.py",
        },
        "tasks": tasks,
    }


def main() -> int:
    manifest = build()
    OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    cats = {}
    for t in manifest["tasks"]:
        e = t if "category" in t else t.get("extra", {})
        c = t.get("category") or e.get("category", "?")
        cats[c] = cats.get(c, 0) + 1
    print(f"Wrote {len(manifest['tasks'])} tasks → {OUT}")
    print("categories:", cats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
