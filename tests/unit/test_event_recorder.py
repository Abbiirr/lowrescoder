"""Tests for EventRecorder — fail-open training event capture."""

from __future__ import annotations

import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from hybridcoder.agent.event_recorder import EventRecorder
from hybridcoder.core.blob_store import BlobStore
from hybridcoder.session.episode_store import EpisodeStore
from hybridcoder.session.models import ensure_tables


@pytest.fixture()
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_tables(conn)
    return conn


@pytest.fixture()
def blob_store(tmp_path):
    return BlobStore(tmp_path / "blobs")


@pytest.fixture()
def episode_store(db_conn, blob_store):
    return EpisodeStore(db_conn, "session-1", blob_store)


@pytest.fixture()
def recorder(episode_store):
    return EventRecorder(episode_store)


def _make_response(content="Hello", tool_calls=None, reasoning=None, finish_reason="stop"):
    """Create a mock LLMResponse."""
    return SimpleNamespace(
        content=content,
        tool_calls=tool_calls or [],
        reasoning=reasoning,
        finish_reason=finish_reason,
        usage={"prompt_tokens": 10, "completion_tokens": 5},
    )


class TestEventRecorder:
    def test_full_turn_lifecycle(self, recorder, episode_store):
        """start -> request -> response -> end records all events."""
        eid = recorder.on_turn_start("Hello world")
        assert eid is not None

        recorder.on_model_request(eid, [{"role": "user", "content": "Hello"}], [], 0)
        recorder.on_model_response(eid, _make_response(), 100, 0)
        recorder.on_turn_end(eid, "Hi there!", "text_response", {"iterations": 1})

        events = episode_store.get_episode_events(eid)
        types = [e["event_type"] for e in events]
        assert "user_message" in types
        assert "model_request" in types
        assert "model_response" in types
        assert "final_answer" in types

        ep = episode_store.get_episode(eid)
        assert ep["outcome"] == "text_response"

    def test_tool_call_events(self, recorder, episode_store):
        """tool_call + tool_result events are recorded."""
        eid = recorder.on_turn_start("Run tests")
        assert eid is not None

        recorder.on_tool_call(eid, "run_command", {"command": "pytest"}, "tc-1")
        recorder.on_tool_result(eid, "run_command", "All tests passed", "completed", 500)

        events = episode_store.get_episode_events(eid)
        types = [e["event_type"] for e in events]
        assert "tool_call" in types
        assert "tool_result" in types

        # Verify tool_call data
        tc_event = next(e for e in events if e["event_type"] == "tool_call")
        data = json.loads(tc_event["data"])
        assert data["tool_name"] == "run_command"
        assert data["tool_call_id"] == "tc-1"

    def test_human_feedback_event(self, recorder, episode_store):
        """Denial and approval feedback is recorded."""
        eid = recorder.on_turn_start("Edit file")
        assert eid is not None

        recorder.on_human_feedback(eid, "denial", "write_file")
        recorder.on_human_feedback(eid, "approval", "read_file")

        events = episode_store.get_episode_events(eid)
        feedback_events = [e for e in events if e["event_type"] == "human_feedback"]
        assert len(feedback_events) == 2

        data0 = json.loads(feedback_events[0]["data"])
        assert data0["feedback_type"] == "denial"
        data1 = json.loads(feedback_events[1]["data"])
        assert data1["feedback_type"] == "approval"

    def test_fail_open_on_error(self, recorder):
        """DB errors are logged as warnings but don't raise."""
        # Force an error by passing an invalid episode_id
        with patch.object(recorder._store, "add_event", side_effect=RuntimeError("DB error")):
            # Should not raise
            recorder.on_model_request("bad-id", [], [], 0)
            recorder.on_model_response("bad-id", _make_response(), 0, 0)
            recorder.on_tool_call("bad-id", "test", {}, "tc-1")
            recorder.on_tool_result("bad-id", "test", "ok", "completed", 0)
            recorder.on_human_feedback("bad-id", "denial", "test")
            recorder.on_human_edit("bad-id", "draft", "edited")
            recorder.on_turn_end("bad-id", "done", "text_response", {})

        # on_turn_start with a broken start_episode
        with patch.object(recorder._store, "start_episode", side_effect=RuntimeError("DB error")):
            result = recorder.on_turn_start("test")
            assert result is None
