"""Coverage inventory for the benchmark + eval suite (Phase 2, build step 1).

Scans every task source — lane manifests (`benchmarks/e2e/external/*.json`),
ai_verification canary scenarios, and `evals/cases/*.yaml` — and tabulates coverage across
difficulty / language / category so empty cells in the target matrix are visible.

Network-free, read-only. Writes `benchmarks/docs/suite-coverage-inventory.md`.

    uv run python benchmarks/inventory_suite.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

MANIFEST_DIR = _ROOT / "benchmarks" / "e2e" / "external"
CANARY_DIR = _ROOT / "benchmarks" / "ai_verification" / "canary_scenarios"
EVAL_DIR = _ROOT / "evals" / "cases"
OUT = _ROOT / "benchmarks" / "docs" / "suite-coverage-inventory.md"


def _norm(v: str) -> str:
    return (v or "").strip().lower() or "unspecified"


def collect() -> list[dict]:
    rows: list[dict] = []

    # 1) Lane manifests
    for mf in sorted(MANIFEST_DIR.glob("*.json")):
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict) or "tasks" not in data:
            continue
        for t in data.get("tasks", []):
            extra = {k: v for k, v in t.items()}
            rows.append({
                "source": f"manifest:{mf.stem}",
                "task_id": t.get("task_id", "?"),
                "difficulty": _norm(t.get("difficulty") or extra.get("difficulty", "")),
                "language": _norm(t.get("language") or extra.get("language", "")),
                "category": _norm(t.get("category") or extra.get("category", "")),
                "has_grading": bool(t.get("grading_command")),
                "has_fail_to_pass": bool(t.get("FAIL_TO_PASS") or t.get("extra", {}).get("FAIL_TO_PASS")) if isinstance(t.get("extra"), dict) else bool(t.get("FAIL_TO_PASS")),
            })

    # 2) ai_verification canary scenarios
    for cf in sorted(CANARY_DIR.glob("*.json")):
        try:
            data = json.loads(cf.read_text(encoding="utf-8"))
        except Exception:
            continue
        stack = data.get("target_stack", {}) or {}
        grading = data.get("grading", {}) or {}
        rows.append({
            "source": "ai_verification:canary",
            "task_id": data.get("scenario_id", cf.stem),
            "difficulty": _norm(data.get("difficulty", "")),
            "language": _norm(stack.get("language", "")),
            "category": _norm(data.get("category", "")),
            "has_grading": bool(grading.get("check_commands")),
            "has_fail_to_pass": False,
        })

    # 3) eval cases (YAML; parse minimally without a yaml dep)
    for ef in sorted(EVAL_DIR.glob("*.yaml")):
        if ef.name.startswith("_"):
            continue
        text = ef.read_text(encoding="utf-8")
        rows.append({
            "source": "evals:case",
            "task_id": ef.stem,
            "difficulty": "unspecified",
            "language": "unspecified",
            "category": "eval",
            "has_grading": "judge_criteria" in text or "must_have" in text,
            "has_fail_to_pass": False,
        })

    return rows


def render(rows: list[dict]) -> str:
    by_diff = Counter(r["difficulty"] for r in rows)
    by_lang = Counter(r["language"] for r in rows)
    by_cat = Counter(r["category"] for r in rows)
    by_source = Counter(r["source"].split(":")[0] for r in rows)
    graded = sum(1 for r in rows if r["has_grading"])
    f2p = sum(1 for r in rows if r["has_fail_to_pass"])

    def table(title: str, counter: Counter) -> list[str]:
        out = [f"### {title}", "", "| value | tasks |", "|---|---|"]
        out += [f"| {k} | {v} |" for k, v in counter.most_common()]
        out += [""]
        return out

    lines = [
        "# Suite Coverage Inventory",
        "",
        f"Total tasks scanned: **{len(rows)}** "
        f"(graded: {graded}, with FAIL_TO_PASS: {f2p})",
        "",
        "Sources: " + ", ".join(f"{k}={v}" for k, v in by_source.most_common()),
        "",
        *table("By difficulty", by_diff),
        *table("By language", by_lang),
        *table("By category", by_cat),
        "## Gaps vs Phase 2 target matrix",
        "",
        "Target (from the Phase 2 spec): difficulty ~30/45/25% easy/medium/hard; ≥2 non-python",
        "tasks per language; ≥3 tasks per category in the full tier. Cells below the bar:",
        "",
    ]
    # Normalise language aliases so coverage is counted under one canonical key.
    lang_alias = {"ts": "typescript", "js": "javascript", "shell": "bash", "sh": "bash"}
    lang_norm: Counter = Counter()
    for k, v in by_lang.items():
        lang_norm[lang_alias.get(k, k)] += v

    gaps = []
    for lang in ("go", "rust", "typescript", "bash", "javascript"):
        if lang_norm.get(lang, 0) < 2:
            gaps.append(f"- language `{lang}`: only {lang_norm.get(lang, 0)} task(s)")
    for need in ("migration", "security", "long_horizon", "refactor", "bugfix"):
        if by_cat.get(need, 0) < 3:
            gaps.append(f"- category `{need}`: only {by_cat.get(need, 0)} task(s)")
    # Difficulty balance vs the 30/45/25 target (hard is the usual shortfall).
    total = len(rows) or 1
    hard_pct = round(100 * by_diff.get("hard", 0) / total)
    if hard_pct < 20:
        gaps.append(
            f"- hard tasks only {hard_pct}% ({by_diff.get('hard', 0)}/{total}) vs ~25% target "
            "— the suite skews easy/medium"
        )
    untagged_lang = by_lang.get("unspecified", 0)
    untagged_cat = by_cat.get("unspecified", 0)
    if untagged_lang or untagged_cat:
        gaps.append(
            f"- {untagged_lang} tasks untagged-language, {untagged_cat} untagged-category "
            "— tag before relying on stratified sampling"
        )
    if f2p < 20:
        gaps.append(
            f"- only {f2p} tasks carry FAIL_TO_PASS metadata — the FAIL_TO_PASS+PASS_TO_PASS "
            "regression-pair discipline (Phase 2 §5) is thin outside the SWE-bench lanes"
        )
    lines += gaps or ["- (no obvious gaps under the simple thresholds)"]
    lines += [
        "",
        "> Generated by `benchmarks/inventory_suite.py` (read-only).",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    rows = collect()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(rows), encoding="utf-8")
    print(f"Scanned {len(rows)} tasks → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
