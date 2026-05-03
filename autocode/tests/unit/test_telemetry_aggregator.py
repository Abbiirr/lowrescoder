from __future__ import annotations

import json


def _write_event(path, *, kind, session_id="s1", ts="2026-04-30T00:00:00Z", data=None):
    event = {
        "ts": ts,
        "session_id": session_id,
        "thread_id": None,
        "turn_id": None,
        "kind": kind,
        "data": data or {},
    }
    with path.open("a") as f:
        f.write(json.dumps(event) + "\n")


def test_summary_groups_by_kind_and_session(tmp_path):
    from autocode.telemetry.aggregator import TelemetryAggregator

    event_file = tmp_path / "events-2026-04-30.jsonl"
    _write_event(event_file, kind="turn_start", session_id="s1")
    _write_event(event_file, kind="turn_start", session_id="s2")
    _write_event(event_file, kind="turn_completed", session_id="s1")

    summary = TelemetryAggregator(root=tmp_path).summary()

    assert summary.total_events == 3
    assert summary.by_kind == {"turn_start": 2, "turn_completed": 1}
    assert summary.by_session == {"s1": 2, "s2": 1}


def test_events_filter_by_kind_and_session(tmp_path):
    from autocode.telemetry.aggregator import TelemetryAggregator

    event_file = tmp_path / "events-2026-04-30.jsonl"
    _write_event(event_file, kind="tool_call_completed", session_id="s1")
    _write_event(event_file, kind="tool_call_failed", session_id="s1")
    _write_event(event_file, kind="tool_call_completed", session_id="s2")

    events = TelemetryAggregator(root=tmp_path).events(
        kind="tool_call_completed",
        session_id="s1",
    )

    assert len(events) == 1
    assert events[0]["kind"] == "tool_call_completed"
    assert events[0]["session_id"] == "s1"


def test_export_csv_contains_header_and_rows(tmp_path):
    from autocode.telemetry.aggregator import TelemetryAggregator

    event_file = tmp_path / "events-2026-04-30.jsonl"
    _write_event(event_file, kind="slash_command_invoked", session_id="s1")

    csv_text = TelemetryAggregator(root=tmp_path).export_csv()

    assert csv_text.splitlines()[0] == "ts,session_id,thread_id,turn_id,kind,data"
    assert "slash_command_invoked" in csv_text


def test_drift_summary_groups_by_tool_kind_and_severity(tmp_path):
    from autocode.telemetry.aggregator import TelemetryAggregator

    event_file = tmp_path / "events-2026-04-30.jsonl"
    _write_event(
        event_file,
        kind="tool_drift_detected",
        data={"tool_name": "read_file", "drift_kind": "schema_drift", "severity": "medium"},
    )
    _write_event(
        event_file,
        kind="tool_drift_detected",
        data={"tool_name": "read_file", "drift_kind": "schema_drift", "severity": "medium"},
    )
    _write_event(
        event_file,
        kind="tool_drift_detected",
        data={"tool_name": "git_status", "drift_kind": "tool_inconsistency", "severity": "high"},
    )

    summary = TelemetryAggregator(root=tmp_path).drift_summary()

    assert summary == {
        ("read_file", "schema_drift", "medium"): 2,
        ("git_status", "tool_inconsistency", "high"): 1,
    }


def test_telemetry_modules_do_not_import_network_clients():
    from pathlib import Path

    telemetry_root = Path("autocode/src/autocode/telemetry")
    forbidden = ("requests", "urllib", "http", "socket")

    for path in telemetry_root.glob("*.py"):
        text = path.read_text()
        for name in forbidden:
            assert f"import {name}" not in text
            assert f"from {name}" not in text
