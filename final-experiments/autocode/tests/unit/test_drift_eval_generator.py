"""Tests for drift-derived eval proposal generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.scripts.generate_evals_from_drift import (  # noqa: E402
    load_drift_events,
    propose_eval_cases,
    write_proposals,
)


def test_drift_generator_proposes_case_after_threshold(tmp_path):
    events = [
        {
            "kind": "tool_drift_detected",
            "data": {"tool_name": "db_rows", "drift_kind": "schema_drift"},
        }
        for _ in range(3)
    ]

    proposals = propose_eval_cases(events, threshold=3)

    assert len(proposals) == 1
    assert proposals[0]["id"] == "drift-db-rows-schema-drift"
    assert proposals[0]["proposal_meta"]["occurrences_30d"] == 3


def test_drift_generator_reads_jsonl_and_writes_yaml(tmp_path):
    telemetry = tmp_path / "events-2026-05-04.jsonl"
    telemetry.write_text(
        "\n".join(
            json.dumps({
                "kind": "tool_drift_detected",
                "data": {"tool_name": "search", "drift_kind": "fact_conflict"},
            })
            for _ in range(3)
        ),
        encoding="utf-8",
    )

    events = load_drift_events(telemetry)
    paths = write_proposals(propose_eval_cases(events), tmp_path / "out")

    assert len(paths) == 1
    assert "drift-search-fact-conflict" in paths[0].read_text(encoding="utf-8")


def test_drift_generator_seeds_fixture_from_source_session_metadata(tmp_path):
    events = [
        {
            "kind": "tool_drift_detected",
            "session_id": "session-a",
            "data": {
                "tool_name": "search",
                "drift_kind": "fact_conflict",
                "project_root": str(tmp_path / "source-project"),
                "fixture_files": {"README.md": "# source\n"},
            },
        },
        {
            "kind": "tool_drift_detected",
            "session_id": "session-b",
            "data": {"tool_name": "search", "drift_kind": "fact_conflict"},
        },
        {
            "kind": "tool_drift_detected",
            "session_id": "session-a",
            "data": {"tool_name": "search", "drift_kind": "fact_conflict"},
        },
    ]

    proposals = propose_eval_cases(events, threshold=3)

    assert proposals[0]["setup"]["fixture_repo"] == str(tmp_path / "source-project")
    assert proposals[0]["setup"]["initial_files"] == {"README.md": "# source\n"}
    assert proposals[0]["proposal_meta"]["source_session_ids"] == [
        "session-a",
        "session-b",
    ]
