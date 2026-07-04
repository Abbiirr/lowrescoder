"""Tests for EpisodeStore — SQLite episode/event CRUD with retention."""

import inspect
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


def _insert_episode_with_events(
    conn: sqlite3.Connection,
    session_id: str,
    seq: int,
    event_types: list[str],
) -> str:
    episode_id = f"ep-{seq}"
    conn.execute(
        "INSERT INTO episodes (id, session_id, sequence_num, started_at, outcome, metrics) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            episode_id,
            session_id,
            seq,
            f"2026-04-25T00:00:{seq:02d}+00:00",
            "summary" if event_types == ["summary"] else "text_response",
            "{}",
        ),
    )
    for idx, event_type in enumerate(event_types):
        conn.execute(
            "INSERT INTO episode_events (episode_id, event_type, timestamp, data) "
            "VALUES (?, ?, ?, ?)",
            (
                episode_id,
                event_type,
                f"2026-04-25T00:00:{seq:02d}.{idx:06d}+00:00",
                json.dumps({"seq": seq, "idx": idx}),
            ),
        )
    conn.commit()
    return episode_id


def _summary_events(conn: sqlite3.Connection) -> list[dict]:
    cursor = conn.execute(
        "SELECT ee.*, e.sequence_num FROM episode_events ee "
        "JOIN episodes e ON e.id = ee.episode_id "
        "WHERE ee.event_type = 'summary' ORDER BY e.sequence_num ASC, ee.id ASC",
    )
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


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
        """Oldest episodes are summarized when exceeding max_episodes_per_session."""
        store = EpisodeStore(db_conn, "session-1", blob_store, max_episodes=3)

        eids = []
        for i in range(4):
            eid = store.start_episode(f"Message {i}")
            eids.append(eid)

        eps = store.list_episodes()
        assert len(eps) == 3
        # The two oldest are folded into one summary to make room for the new turn.
        remaining_ids = {e["id"] for e in eps}
        assert eids[0] not in remaining_ids
        assert eids[1] not in remaining_ids
        assert eids[2] in remaining_ids
        assert eids[3] in remaining_ids

        summary_rows = _summary_events(db_conn)
        assert len(summary_rows) == 1
        payload = json.loads(summary_rows[0]["data"])
        assert payload["event_counts"] == {"user_message": 2}


class TestSummarization:
    def test_enforce_retention_summarizes_oldest_tranche(self, db_conn, blob_store):
        """Retention folds the oldest tranche into a deterministic summary event."""
        store = EpisodeStore(db_conn, "session-1", blob_store, max_episodes=5)
        event_cycle = ["tool_call", "tool_result", "model_response"]
        for seq in range(15):
            _insert_episode_with_events(
                db_conn,
                "session-1",
                seq,
                [event_cycle[seq % len(event_cycle)]],
            )

        store._enforce_retention()

        summary_rows = _summary_events(db_conn)
        assert len(summary_rows) == 1
        payload = json.loads(summary_rows[0]["data"])
        assert payload == {
            "event_counts": {
                "tool_call": 4,
                "tool_result": 4,
                "model_response": 4,
            },
            "ts_range": [
                "2026-04-25T00:00:00.000000+00:00",
                "2026-04-25T00:00:11.000000+00:00",
            ],
            "n_collapsed": 12,
        }
        assert [ep["sequence_num"] for ep in store.list_episodes()] == [0, 12, 13, 14]

    def test_summary_event_schema(self, db_conn, blob_store):
        """Summary payload only contains the public deterministic schema."""
        store = EpisodeStore(db_conn, "session-1", blob_store, max_episodes=3)
        for seq, event_type in enumerate(["tool_call", "error", "completion"]):
            _insert_episode_with_events(db_conn, "session-1", seq, [event_type])

        store._enforce_retention()

        summary_rows = _summary_events(db_conn)
        assert len(summary_rows) == 1
        payload = json.loads(summary_rows[0]["data"])
        assert set(payload) == {"event_counts", "ts_range", "n_collapsed"}
        assert isinstance(payload["event_counts"], dict)
        assert len(payload["ts_range"]) == 2
        assert payload["n_collapsed"] == 2

    def test_recursion_cap_drops_oldest_summary(self, db_conn, blob_store):
        """When summaries dominate remaining history, drop the oldest summary."""
        store = EpisodeStore(db_conn, "session-1", blob_store, max_episodes=5)
        _insert_episode_with_events(db_conn, "session-1", 0, ["tool_call"])
        oldest_summary = _insert_episode_with_events(db_conn, "session-1", 1, ["summary"])
        _insert_episode_with_events(db_conn, "session-1", 2, ["summary"])
        _insert_episode_with_events(db_conn, "session-1", 3, ["summary"])
        _insert_episode_with_events(db_conn, "session-1", 4, ["tool_result"])

        store._enforce_retention()

        remaining_ids = {ep["id"] for ep in store.list_episodes()}
        assert "ep-0" in remaining_ids
        assert oldest_summary not in remaining_ids
        assert len(_summary_events(db_conn)) == 2

    def test_retention_synchronous(self):
        """Retention stays inline-safe for the agent loop call path."""
        assert inspect.iscoroutinefunction(EpisodeStore._enforce_retention) is False

    def test_zero_events_noop(self, db_conn, blob_store):
        """Empty stores are not mutated or errored by retention."""
        store = EpisodeStore(db_conn, "session-1", blob_store, max_episodes=3)
        store._enforce_retention()
        assert store.list_episodes() == []

    def test_retention_below_bound_noop(self, db_conn, blob_store):
        """Below-bound stores remain unchanged."""
        store = EpisodeStore(db_conn, "session-1", blob_store, max_episodes=5)
        inserted = [
            _insert_episode_with_events(db_conn, "session-1", seq, ["tool_call"])
            for seq in range(2)
        ]

        store._enforce_retention()

        assert [ep["id"] for ep in store.list_episodes()] == inserted
