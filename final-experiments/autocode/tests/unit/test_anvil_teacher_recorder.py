"""Tests for the trajectory recorder (G2 / §4.2.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from autocode.anvil.teacher.recorder import from_autocode_ndjson, from_puku_stream
from autocode.anvil.teacher.schemas import Layer, ModelInfo, Task

# The frozen real puku stream-json capture lives in the harness-tester repo.
_PUKU_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "harness-tester"
    / "tests"
    / "fixtures"
    / "puku_cli_stream.jsonl"
)


def test_autocode_ndjson_typed_tool_events() -> None:
    events = [
        {"type": "thread_started", "thread_id": "t1"},
        {
            "type": "tool_call_started",
            "tool_call_id": "c1",
            "tool_name": "search_text",
            "tool_family": "search",
        },
        {"type": "tool_call_completed", "tool_call_id": "c1", "tool_name": "search_text"},
        {
            "type": "tool_call_started",
            "tool_call_id": "c2",
            "tool_name": "edit_file",
            "tool_family": "file_write",
        },
        {"type": "item_completed", "item_id": "x", "result": "patched mathutil.py"},
        {"type": "turn_completed", "usage": {"input_tokens": 1000, "output_tokens": 200}},
    ]
    tj = from_autocode_ndjson(
        events,
        trajectory_id="tj_ac",
        task=Task(instruction="add function"),
        model=ModelInfo(alias="coding", provider="openai", is_local=True),
        final_diff="--- a\n+++ b\n",
        wall_s=4.2,
    )
    # Two tool steps, deduped (started/completed for c1 collapse to one).
    assert len(tj.steps) == 2
    assert tj.steps[0].tool == "search_text"
    assert tj.steps[0].layer == Layer.L2.value
    assert tj.steps[1].tool == "edit_file"
    assert tj.steps[1].layer == Layer.L4.value
    # observation digest attached from item_completed result
    assert tj.steps[1].observation_digest.startswith("sha256:")
    # layer distribution computed
    assert tj.layer_distribution["L2"] == 0.5
    assert tj.layer_distribution["L4"] == 0.5
    assert tj.cost["wall_s"] == 4.2
    assert tj.role == "student"


def test_autocode_ndjson_legacy_item_events() -> None:
    events = [
        {
            "type": "item_started",
            "item_id": "i1",
            "kind": "tool_execution",
            "tool_name": "grep_content",
        },
        {
            "type": "item_started",
            "item_id": "i2",
            "kind": "tool_execution",
            "tool_name": "write_file",
        },
    ]
    tj = from_autocode_ndjson(events, trajectory_id="tj_legacy", task=Task(instruction="x"))
    assert len(tj.steps) == 2
    assert tj.steps[0].layer == Layer.L2.value  # search family
    assert tj.steps[1].layer == Layer.L4.value  # file_write family


def test_puku_stream_synthetic() -> None:
    events = [
        {"type": "system", "subtype": "init", "session_id": "s1"},
        {
            "type": "assistant",
            "message": {
                "model": "MiniMax-M3",
                "content": [
                    {"type": "text", "text": "let me look"},
                    {
                        "type": "tool_use",
                        "id": "u1",
                        "name": "Read",
                        "input": {"file_path": "a.py"},
                    },
                ],
            },
        },
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "u1",
                        "content": "file body",
                        "is_error": False,
                    }
                ]
            },
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "id": "u2", "name": "Edit", "input": {"file_path": "a.py"}}
                ]
            },
        },
        {"type": "result", "duration_ms": 5200, "total_cost_usd": 0.0, "num_turns": 3},
    ]
    tj = from_puku_stream(
        events, trajectory_id="tj_puku", task=Task(instruction="x"), final_diff="d"
    )
    assert len(tj.steps) == 2
    assert tj.steps[0].tool == "Read"
    assert tj.steps[0].layer == Layer.L2.value
    assert tj.steps[0].observation_digest.startswith("sha256:")
    assert tj.steps[1].tool == "Edit"
    assert tj.steps[1].layer == Layer.L4.value
    assert tj.model.alias == "MiniMax-M3"
    assert tj.cost["wall_s"] == 5.2
    assert tj.role == "teacher"


def test_puku_stream_marks_observed_errors() -> None:
    events = [
        {
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "id": "u1", "name": "Read", "input": {}}]},
        },
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "u1",
                        "content": "nope",
                        "is_error": True,
                    }
                ]
            },
        },
    ]
    tj = from_puku_stream(events, trajectory_id="tj_e", task=Task(instruction="x"))
    assert tj.steps[0].args.get("_observed_error") is True


@pytest.mark.skipif(not _PUKU_FIXTURE.is_file(), reason="puku stream fixture not present")
def test_puku_stream_on_frozen_real_capture() -> None:
    text = _PUKU_FIXTURE.read_text(encoding="utf-8")
    tj = from_puku_stream(
        text, trajectory_id="tj_real", task=Task(instruction="add add() to mathutil")
    )
    # The real capture contains Bash/Read/Edit tool calls.
    assert len(tj.steps) >= 3
    tools = {s.tool for s in tj.steps}
    assert tools & {"Bash", "Read", "Edit"}
    # At least one retrieval-layer step and one action-layer step.
    layers = {s.layer for s in tj.steps}
    assert Layer.L4.value in layers
    assert sum(tj.layer_distribution.values()) == pytest.approx(1.0)
