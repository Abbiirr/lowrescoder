from __future__ import annotations

import json
import time
from datetime import UTC, datetime


def test_store_writes_jsonl_event_with_common_envelope(tmp_path):
    from autocode.telemetry.store import TelemetryStore

    store = TelemetryStore(root=tmp_path)
    store.emit(
        "turn_completed",
        session_id="s1",
        thread_id="t1",
        turn_id="u1",
        data={"duration_ms": 12},
        ts=datetime(2026, 4, 30, tzinfo=UTC),
    )
    store.shutdown()

    lines = (tmp_path / "events-2026-04-30.jsonl").read_text().splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event == {
        "ts": "2026-04-30T00:00:00Z",
        "session_id": "s1",
        "thread_id": "t1",
        "turn_id": "u1",
        "kind": "turn_completed",
        "data": {"duration_ms": 12},
    }


def test_store_disable_flag_makes_emit_noop(tmp_path, monkeypatch):
    from autocode.telemetry.store import TelemetryStore

    monkeypatch.setenv("AUTOCODE_TELEMETRY_DISABLED", "true")
    store = TelemetryStore(root=tmp_path)
    assert store.emit("session_start", session_id="s1") is False
    store.shutdown()

    assert list(tmp_path.glob("*.jsonl")) == []


def test_store_drops_when_queue_full_without_blocking(tmp_path):
    from autocode.telemetry.store import TelemetryStore

    store = TelemetryStore(root=tmp_path, max_queue=1, autostart=False)

    assert store.emit("turn_start", session_id="s1") is True
    assert store.emit("turn_completed", session_id="s1") is False
    assert store.dropped_count == 1
    store.shutdown()


def test_store_rotates_files_by_event_date(tmp_path):
    from autocode.telemetry.store import TelemetryStore

    store = TelemetryStore(root=tmp_path)
    store.emit("session_start", ts=datetime(2026, 4, 30, tzinfo=UTC))
    store.emit("session_end", ts=datetime(2026, 5, 1, tzinfo=UTC))
    store.shutdown()

    assert (tmp_path / "events-2026-04-30.jsonl").exists()
    assert (tmp_path / "events-2026-05-01.jsonl").exists()


def test_emit_hot_path_stays_under_budget(tmp_path):
    from autocode.telemetry.store import TelemetryStore

    store = TelemetryStore(root=tmp_path, autostart=False)
    timings = []
    for _ in range(5):
        start = time.perf_counter()
        for _ in range(1000):
            store.emit("tool_call_completed", data={"tool_name": "read_file"})
        timings.append(((time.perf_counter() - start) / 1000) * 1_000_000)
    elapsed_us = min(timings)
    store.shutdown()

    assert elapsed_us < 5
