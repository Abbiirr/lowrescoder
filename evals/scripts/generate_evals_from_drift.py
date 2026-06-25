#!/usr/bin/env python3
"""Propose eval cases from recurring drift telemetry events."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


def load_drift_events(path: Path) -> list[dict[str, Any]]:
    paths = sorted(path.glob("events-*.jsonl")) if path.is_dir() else [path]
    events: list[dict[str, Any]] = []
    for item in paths:
        if not item.exists():
            continue
        for line in item.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("kind") == "tool_drift_detected":
                events.append(event)
    return events


def propose_eval_cases(events: list[dict[str, Any]], *, threshold: int = 3) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    grouped_events: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for event in events:
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        tool_name = str(data.get("tool_name") or "unknown_tool")
        drift_kind = str(data.get("drift_kind") or "unknown_drift")
        counts[(tool_name, drift_kind)] += 1
        grouped_events.setdefault((tool_name, drift_kind), []).append(event)

    proposals: list[dict[str, Any]] = []
    for (tool_name, drift_kind), count in sorted(counts.items()):
        if count < threshold:
            continue
        case_id = f"drift-{tool_name}-{drift_kind}".replace("_", "-")
        group = grouped_events.get((tool_name, drift_kind), [])
        seed = _select_seed_event(group)
        seed_data = seed.get("data") if isinstance(seed.get("data"), dict) else {}
        proposals.append({
            "id": case_id,
            "name": f"Recurring drift: {tool_name} {drift_kind}",
            "provenance": {
                "source": "telemetry-drift",
                "bug_id": case_id,
                "recorded_at": "",
            },
            "setup": {
                "fixture_repo": _fixture_repo_from(seed_data),
                "initial_files": _initial_files_from(seed_data),
            },
            "input": {
                "user_message": (
                    f"Reproduce and prevent recurring {drift_kind} for tool {tool_name}."
                )
            },
            "expected_outcomes": {
                "must_have": ["turn_completed"],
                "must_not_have": ["tool_drift_detected"],
                "judge_criteria": ["correctness"],
            },
            "config": {
                "model": "coding",
                "max_turns": 3,
                "timeout_sec": 120,
                "temperature": 0.0,
                "seed": 0,
            },
            "baseline": {
                "correctness_score": 0.90,
                "minimality_score": 0.80,
                "test_quality_score": 0.75,
                "cost_usd_p50": 0.25,
            },
            "archived": False,
            "proposal_meta": {
                "occurrences_30d": count,
                "tool_name": tool_name,
                "drift_kind": drift_kind,
                "source_session_ids": _source_session_ids(group),
            },
        })
    return proposals


def _select_seed_event(events: list[dict[str, Any]]) -> dict[str, Any]:
    for event in events:
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        if _fixture_repo_from(data) or _initial_files_from(data):
            return event
    return events[0] if events else {}


def _fixture_repo_from(data: dict[str, Any]) -> str:
    return str(data.get("fixture_repo") or data.get("project_root") or "")


def _initial_files_from(data: dict[str, Any]) -> dict[str, str]:
    raw = data.get("fixture_files") or data.get("initial_files") or {}
    if not isinstance(raw, dict):
        return {}
    return {str(path): str(content) for path, content in raw.items()}


def _source_session_ids(events: list[dict[str, Any]]) -> list[str]:
    ids = {
        str(event.get("session_id"))
        for event in events
        if event.get("session_id")
    }
    return sorted(ids)


def write_proposals(proposals: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for proposal in proposals:
        path = output_dir / f"{proposal['id']}.yaml"
        path.write_text(yaml.safe_dump(proposal, sort_keys=False), encoding="utf-8")
        paths.append(path)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--telemetry", type=Path, default=Path.home() / ".autocode" / "telemetry")
    parser.add_argument("--output-dir", type=Path, default=Path("evals/cases/proposed"))
    parser.add_argument("--threshold", type=int, default=3)
    args = parser.parse_args()

    proposals = propose_eval_cases(
        load_drift_events(args.telemetry),
        threshold=args.threshold,
    )
    paths = write_proposals(proposals, args.output_dir)
    print(json.dumps({"proposal_count": len(paths), "paths": [str(path) for path in paths]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
