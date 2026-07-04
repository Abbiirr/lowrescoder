from __future__ import annotations

import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from autocode.agent.drift import (
    ContextStalenessDetector,
    DriftWarning,
    SchemaDriftDetector,
    ToolConsistencyDetector,
    args_hash,
    format_drift_warning,
)
from autocode.layer4.llm import ToolCall


def test_args_hash_is_deterministic_for_sorted_json() -> None:
    assert args_hash({"b": 2, "a": 1}) == args_hash({"a": 1, "b": 2})
    assert len(args_hash({"a": 1})) == 16


def test_compute_shape_handles_nested_structures_and_depth_limit() -> None:
    detector = SchemaDriftDetector()

    shape = detector._compute_shape({"rows": [{"email": "a", "ok": True}]}, max_depth=1)

    assert shape == {"rows": [{"__truncated": True}]}


def test_schema_drift_fires_on_column_rename() -> None:
    detector = SchemaDriftDetector()
    detector.observe("db_rows", {"query": "users"}, [{"email_certified": True}])

    warning = detector.observe("db_rows", {"query": "users"}, [{"email_verified": True}])

    assert warning is not None
    assert warning.kind == "schema_drift"
    assert warning.severity in {"medium", "high"}
    assert "email_certified" in str(warning.diff)
    assert "email_verified" in str(warning.diff)


def test_schema_drift_low_sensitivity_ignores_type_changes() -> None:
    detector = SchemaDriftDetector(sensitivity="low")
    detector.observe("db_rows", {"query": "users"}, [{"count": 1}])

    warning = detector.observe("db_rows", {"query": "users"}, [{"count": "1"}])

    assert warning is None


def test_schema_drift_high_sensitivity_fires_on_new_keys() -> None:
    detector = SchemaDriftDetector(sensitivity="high")
    detector.observe("db_rows", {"query": "users"}, [{"id": 1}])

    warning = detector.observe("db_rows", {"query": "users"}, [{"id": 1, "email": "a"}])

    assert warning is not None
    assert warning.kind == "schema_drift"


def test_context_staleness_detector_warns_on_old_topic(tmp_path: Path) -> None:
    topic = tmp_path / "memory" / "api.md"
    topic.parent.mkdir(parents=True)
    topic.write_text("old fact", encoding="utf-8")
    old = datetime.now(UTC) - timedelta(days=9)
    os.utime(topic, (old.timestamp(), old.timestamp()))
    memory_fs = StubMemoryFS(topics_dir=topic.parent)

    warning = ContextStalenessDetector(
        memory_fs,
        threshold=timedelta(days=7),
    ).check_fact_freshness("api")

    assert warning is not None
    assert warning.kind == "context_staleness"
    assert warning.severity == "medium"


def test_tool_consistency_detector_warns_on_same_turn_change() -> None:
    detector = ToolConsistencyDetector()
    detector.observe("read_file", {"path": "a.py"}, "one")

    warning = detector.observe("read_file", {"path": "a.py"}, "two")

    assert warning is not None
    assert warning.kind == "tool_inconsistency"
    assert warning.severity == "high"


def test_tool_consistency_reset_turn_clears_observations() -> None:
    detector = ToolConsistencyDetector()
    detector.observe("read_file", {"path": "a.py"}, "one")
    detector.reset_turn()

    warning = detector.observe("read_file", {"path": "a.py"}, "two")

    assert warning is None


def test_warning_injection_format_matches_contract() -> None:
    warning = DriftWarning(
        kind="schema_drift",
        severity="medium",
        recommendation="Verify assumptions.",
        diff={"missing": ["old"]},
        tool_name="db_rows",
    )

    formatted = format_drift_warning(warning)

    assert formatted.startswith("[Drift detected — schema_drift, severity medium]")
    assert "Acknowledge this warning in your next response" in formatted
    assert '"missing"' in formatted


def test_detector_latency_under_five_ms() -> None:
    detector = SchemaDriftDetector(sensitivity="high")
    detector.observe("db_rows", {"query": "users"}, [{"id": 1}])

    start = time.perf_counter()
    for idx in range(100):
        detector.observe("db_rows", {"query": "users"}, [{"id": idx, "email": "a"}])
    per_detection_ms = ((time.perf_counter() - start) / 100) * 1000

    assert per_detection_ms < 5


def test_per_detector_disable_flag_is_honored() -> None:
    detector = SchemaDriftDetector(enabled=False)
    detector.observe("db_rows", {}, [{"old": 1}])

    warning = detector.observe("db_rows", {}, [{"new": 1}])

    assert warning is None


def test_drift_detection_hook_collects_warnings_and_telemetry() -> None:
    from autocode.agent.hooks import DriftDetectionHook

    events: list[tuple[str, dict[str, Any]]] = []
    hook = DriftDetectionHook(
        schema_detector=SchemaDriftDetector(sensitivity="high"),
        consistency_detector=ToolConsistencyDetector(),
        telemetry_emit=lambda kind, data: events.append((kind, data)),
    )
    hook.post_tool_call_success(
        ToolCall(id="tc1", name="db_rows", arguments={"query": "users"}),
        [{"id": 1}],
    )
    hook.post_tool_call_success(
        ToolCall(id="tc2", name="db_rows", arguments={"query": "users"}),
        [{"id": 1, "email": "a"}],
    )

    warnings = hook.drain_warnings()

    assert len(warnings) == 1
    assert warnings[0].startswith("[Drift detected — schema_drift")
    assert events == [
        (
            "tool_drift_detected",
            {
                "tool_name": "db_rows",
                "drift_kind": "schema_drift",
                "severity": "low",
            },
        )
    ]


class StubMemoryFS:
    def __init__(self, *, topics_dir: Path) -> None:
        self.topics_dir = topics_dir
