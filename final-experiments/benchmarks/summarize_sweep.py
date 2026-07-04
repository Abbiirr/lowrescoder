"""Summarize a benchmark sweep into one consolidated per-lane table.

Reads the per-lane progress files written by ``benchmark_runner.py`` for a given run-id and
produces a Markdown summary: tasks run, resolved rate, infra failures, mean agent turns, and
which lanes were blocked/not-executable. Use it to present a full B7–B29 sweep.

    uv run python benchmarks/summarize_sweep.py <run-id> [--agent puku]
    uv run python benchmarks/summarize_sweep.py --latest

Read-only; writes ``benchmarks/docs/sweep-summary-<run-id>.md``.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
QA_DIR = _ROOT / "docs" / "qa" / "test-results"          # durable per-lane artifacts
OUT_DIR = _ROOT / "benchmarks" / "docs"


def _artifacts_for(agent: str) -> list[tuple[str, dict]]:
    """Return (filename, data) for every per-lane artifact written by the given agent."""
    out: list[tuple[str, dict]] = []
    for p in sorted(QA_DIR.glob(f"*-{agent}.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and "contract" in data and "results" in data:
            out.append((p.name, data))
    return out


def _find_run_ids(agent: str | None) -> list[str]:
    ids: set[str] = set()
    for _name, data in _artifacts_for(agent or "puku"):
        rid = (data.get("contract") or {}).get("run_id")
        if rid:
            ids.add(rid)
    return sorted(ids)


def summarize(run_id: str | list[str], agent: str) -> dict:
    # run_id may be a single id or a list — later ids override earlier ones per lane
    # (e.g. an original sweep + targeted re-runs of transient-infra lanes).
    run_ids = [run_id] if isinstance(run_id, str) else list(run_id)
    # Latest artifact per (run_id, lane); filenames are timestamp-sorted ascending.
    per_run_lane: dict[str, dict[str, dict]] = {rid: {} for rid in run_ids}
    contract_meta: dict = {}
    for _name, data in _artifacts_for(agent):
        contract = data.get("contract") or {}
        rid = contract.get("run_id")
        if rid not in per_run_lane:
            continue
        lane = data.get("lane") or contract.get("lane") or "?"
        per_run_lane[rid][lane] = data
        contract_meta = {
            "harness_commit_sha": contract.get("harness_commit_sha"),
            "agent_version": contract.get("agent_version"),
            "model": contract.get("model"),
            "provider_mode": contract.get("provider_mode"),
        }
    # Merge: later run-ids override per lane.
    latest: dict[str, dict] = {}
    for rid in run_ids:
        latest.update(per_run_lane[rid])

    lanes: list[dict] = []
    for lane, data in latest.items():
        results = data.get("results", [])
        agg = data.get("aggregate") or {}
        resolved = agg.get("resolved", sum(1 for r in results if r.get("resolved")))
        infra = agg.get("infra_fails", sum(
            1 for r in results
            if (r.get("artifacts") or {}).get("failure_type") == "INFRA_FAIL"
        ))
        turns = [
            (r.get("artifacts") or {}).get("puku_num_turns")
            for r in results
            if (r.get("artifacts") or {}).get("puku_num_turns") is not None
        ]
        ftypes: dict[str, int] = {}
        for r in results:
            ft = (r.get("artifacts") or {}).get("failure_type", "?")
            ftypes[ft] = ftypes.get(ft, 0) + 1
        lanes.append({
            "lane": lane,
            "tasks": len(results),
            "resolved": resolved,
            "infra_fails": infra,
            "mean_turns": round(statistics.mean(turns), 1) if turns else None,
            "avg_wall_s": agg.get("avg_wall_time_s"),
            "failure_types": ftypes,
        })
    lanes.sort(key=lambda x: x["lane"])
    total_tasks = sum(x["tasks"] for x in lanes)
    total_resolved = sum(x["resolved"] for x in lanes)
    total_infra = sum(x["infra_fails"] for x in lanes)
    return {
        "run_id": run_id,
        "agent": agent,
        "contract": contract_meta,
        "lanes_with_results": len(lanes),
        "total_tasks": total_tasks,
        "total_resolved": total_resolved,
        "overall_resolve_rate": round(total_resolved / total_tasks, 3) if total_tasks else None,
        "total_infra_fails": total_infra,
        "lanes": lanes,
    }


def render(s: dict) -> str:
    c = s.get("contract") or {}
    lines = [
        f"# Sweep Summary — {s['run_id']}",
        "",
        f"Agent: **{s['agent']}** ({c.get('agent_version', '?')})  ·  model: "
        f"`{c.get('model', '?')}` ({c.get('provider_mode', '?')})  ·  harness commit: "
        f"`{(c.get('harness_commit_sha') or '?')[:12]}`",
        "",
        f"Lanes with results: **{s['lanes_with_results']}**  ·  tasks: **{s['total_tasks']}**"
        f"  ·  resolved: **{s['total_resolved']}** ({s['overall_resolve_rate']})"
        f"  ·  infra fails: **{s['total_infra_fails']}**",
        "",
        "> Infra fails are excluded from agent-capability judgements (harness/gateway issues,",
        "> not agent misses). Lanes missing here were blocked (e.g. bash-only for external",
        "> agents) or not yet reached.",
        "",
        "| Lane | Tasks | Resolved | Rate | Infra | Mean turns | Failure types |",
        "|---|---|---|---|---|---|---|",
    ]
    for x in s["lanes"]:
        rate = round(x["resolved"] / x["tasks"], 2) if x["tasks"] else "-"
        fts = ", ".join(f"{k}:{v}" for k, v in sorted(x["failure_types"].items()))
        lines.append(
            f"| {x['lane']} | {x['tasks']} | {x['resolved']} | {rate} | "
            f"{x['infra_fails']} | {x['mean_turns'] if x['mean_turns'] is not None else '-'} | {fts} |"
        )
    lines += ["", "> Generated by `benchmarks/summarize_sweep.py` (read-only)."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Summarize a benchmark sweep")
    ap.add_argument("run_id", nargs="?", help="run id (omit with --latest)")
    ap.add_argument("--agent", default="puku")
    ap.add_argument("--latest", action="store_true", help="use the most recent run id")
    args = ap.parse_args(argv)

    run_id = args.run_id
    if args.latest or not run_id:
        ids = _find_run_ids(args.agent)
        if not ids:
            print(f"No artifacts found for agent={args.agent}", file=sys.stderr)
            return 2
        run_id = ids[-1]

    # Comma-separated run-ids merge (later overrides earlier per lane).
    run_ids = [r.strip() for r in run_id.split(",") if r.strip()]
    s = summarize(run_ids if len(run_ids) > 1 else run_ids[0], args.agent)
    s["run_id"] = "+".join(run_ids)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    label = run_ids[0] + ("-merged" if len(run_ids) > 1 else "")
    out = OUT_DIR / f"sweep-summary-{label}.md"
    out.write_text(render(s), encoding="utf-8")
    print(json.dumps({k: v for k, v in s.items() if k != "lanes"}, indent=2))
    print(f"\nSummary: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
