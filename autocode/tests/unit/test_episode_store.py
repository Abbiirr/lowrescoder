"""Tests for EpisodeStore — SQLite episode/event CRUD with retention."""

from __future__ import annotations

import json
import sqlite3

import pytest

from autocode.core.blob_store import BlobStore
from autocode.session.episode_store import EpisodeStore
from autocode.session.models import ensure_tables


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
    return EpisodeStore(db_conn, "session-1", blob_store, max_episodes=200)


class TestEpisodeStore:
    def test_start_and_end_episode(self, episode_store):
        """Creates an episode with correct sequence_num and can end it."""
        eid = episode_store.start_episode("Hello")
        assert eid is not None

        ep = episode_store.get_episode(eid)
        assert ep is not None
        assert ep["sequence_num"] == 0
        assert ep["session_id"] == "session-1"
        assert ep["outcome"] is None

        episode_store.end_episode(eid, "text_response", {"iterations": 1})
        ep = episode_store.get_episode(eid)
        assert ep["outcome"] == "text_response"
        assert json.loads(ep["metrics"])["iterations"] == 1

    def test_add_events(self, episode_store):
        """Adds events and retrieves them in id order."""
        eid = episode_store.start_episode("Test")
        episode_store.add_event(eid, "model_request", {"iteration": 0})
        episode_store.add_event(eid, "model_response", {"iteration": 0})
        episode_store.add_event(eid, "final_answer", {"text": "done"})

        events = episode_store.get_episode_events(eid)
        # user_message (from start_episode) + 3 added = 4 total
        assert len(events) == 4
        types = [e["event_type"] for e in events]
        assert types == ["user_message", "model_request", "model_response", "final_answer"]

    def test_list_episodes(self, episode_store):
        """Lists episodes for the session."""
        episode_store.start_episode("First")
        episode_store.start_episode("Second")

        eps = episode_store.list_episodes()
        assert len(eps) == 2

    def test_sequence_numbering(self, episode_store):
        """Multiple episodes get incrementing sequence numbers."""
        eid1 = episode_store.start_episode("First")
        eid2 = episode_store.start_episode("Second")
        eid3 = episode_store.start_episode("Third")

        assert episode_store.get_episode(eid1)["sequence_num"] == 0
        assert episode_store.get_episode(eid2)["sequence_num"] == 1
        assert episode_store.get_episode(eid3)["sequence_num"] == 2

    def test_externalize_large_payload(self, episode_store):
        """Large values get externalized to blob references."""
        large = "x" * 2000
        ref = episode_store._externalize_value(large)
        assert "blob_sha256" in ref
        assert "preview" in ref

    def test_get_episode_events_ordered(self, episode_store):
        """Events are returned in id ASC order for deterministic replay."""
        eid = episode_store.start_episode("Order test")
        # Add events in a specific order
        episode_store.add_event(eid, "tool_call", {"name": "read_file"})
        episode_store.add_event(eid, "tool_result", {"name": "read_file"})
        episode_store.add_event(eid, "tool_call", {"name": "write_file"})

        events = episode_store.get_episode_events(eid)
        ids = [e["id"] for e in events]
        assert ids == sorted(ids), "Events should be in ascending ID order"

    def test_retention_enforcement(self, db_conn, blob_store):
        """Oldest episodes are pruned when exceeding max_episodes_per_session."""
        store = EpisodeStore(db_conn, "session-1", blob_store, max_episodes=3)

        eids = []
        for i in range(4):
            eid = store.start_episode(f"Message {i}")
            eids.append(eid)

        eps = store.list_episodes()
        assert len(eps) == 3
        # The oldest (sequence_num=0) should have been pruned
        remaining_ids = {e["id"] for e in eps}
        assert eids[0] not in remaining_ids
        assert eids[1] in remaining_ids
        assert eids[2] in remaining_ids
        assert eids[3] in remaining_ids
