"""Episode store for training-grade event logging."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from collections import Counter
from datetime import UTC, datetime

from autocode.core.blob_store import BlobStore

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class EpisodeStore:
    """CRUD operations for episodes and their events in SQLite."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        session_id: str,
        blob_store: BlobStore,
        max_episodes: int = 200,
    ) -> None:
        self._conn = conn
        self._session_id = session_id
        self._blob_store = blob_store
        self._max_episodes = max_episodes

    def start_episode(self, user_message: str) -> str:
        """Create a new episode and emit the initial user_message event.

        Enforces retention by pruning oldest episodes beyond the cap.
        Returns the episode ID.
        """
        self._enforce_retention()

        # Compute next sequence_num
        row = self._conn.execute(
            "SELECT COALESCE(MAX(sequence_num), -1) FROM episodes WHERE session_id = ?",
            (self._session_id,),
        ).fetchone()
        seq = row[0] + 1

        episode_id = str(uuid.uuid4())
        now = _now_iso()
        self._conn.execute(
            "INSERT INTO episodes (id, session_id, sequence_num, started_at) "
            "VALUES (?, ?, ?, ?)",
            (episode_id, self._session_id, seq, now),
        )
        self._conn.commit()

        # Emit user_message event
        self.add_event(episode_id, "user_message", {
            "text": self._externalize_value(user_message),
            "token_count": max(1, len(user_message) // 4),
        })
        return episode_id

    def add_event(self, episode_id: str, event_type: str, data: dict) -> int:
        """Add an event to an episode. Returns the event row ID."""
        now = _now_iso()
        data_json = json.dumps(data, default=str)
        cursor = self._conn.execute(
            "INSERT INTO episode_events (episode_id, event_type, timestamp, data) "
            "VALUES (?, ?, ?, ?)",
            (episode_id, event_type, now, data_json),
        )
        self._conn.commit()
        return cursor.lastrowid or 0

    def end_episode(self, episode_id: str, outcome: str, metrics: dict) -> None:
        """Mark an episode as completed."""
        now = _now_iso()
        self._conn.execute(
            "UPDATE episodes SET ended_at = ?, outcome = ?, metrics = ? WHERE id = ?",
            (now, outcome, json.dumps(metrics, default=str), episode_id),
        )
        self._conn.commit()

    def get_episode(self, episode_id: str) -> dict | None:
        """Get a single episode by ID."""
        cursor = self._conn.execute(
            "SELECT * FROM episodes WHERE id = ?", (episode_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))

    def get_episode_events(self, episode_id: str) -> list[dict]:
        """Get all events for an episode, ordered by id ASC for deterministic replay."""
        cursor = self._conn.execute(
            "SELECT * FROM episode_events WHERE episode_id = ? ORDER BY id ASC",
            (episode_id,),
        )
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def list_episodes(self, session_id: str | None = None) -> list[dict]:
        """List episodes, optionally filtered by session."""
        sid = session_id or self._session_id
        cursor = self._conn.execute(
            "SELECT * FROM episodes WHERE session_id = ? ORDER BY sequence_num ASC",
            (sid,),
        )
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def _externalize_value(self, data: str) -> dict:
        """Externalize a string value to blob if it's large enough."""
        return self._blob_store.maybe_externalize(data)

    def _externalize(self, data: dict, keys: list[str]) -> dict:
        """Externalize specific keys in a dict to blob if they are large strings."""
        result = dict(data)
        for key in keys:
            val = result.get(key)
            if isinstance(val, str):
                result[key] = self._externalize_value(val)
        return result

    def _enforce_retention(self) -> None:
        """Summarize oldest episodes before pruning beyond max_episodes_per_session."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM episodes WHERE session_id = ?",
            (self._session_id,),
        ).fetchone()
        count = row[0]
        if count < self._max_episodes:
            return

        # Retention runs before creating the next episode, so reserve one slot.
        prune_count = count - self._max_episodes + 1
        collapse_count = prune_count + 1
        if self._max_episodes <= 1 or collapse_count > count:
            self._delete_oldest_episodes(prune_count)
            self._conn.commit()
            return

        oldest = self._oldest_episodes(collapse_count)
        oldest_ids = [row[0] for row in oldest]
        if self._remaining_summary_ratio(excluding_episode_ids=oldest_ids) > 0.5:
            if self._delete_oldest_summary_episode():
                self._prune_until_next_episode_fits()
            else:
                self._delete_oldest_episodes(prune_count)
            self._conn.commit()
            return

        events = self._events_for_episodes(oldest_ids)
        payload = self._summarize_tranche(events)
        summary_episode_id = str(uuid.uuid4())
        summary_sequence_num = oldest[0][1]
        summary_started_at = payload["ts_range"][0]
        summary_ended_at = payload["ts_range"][1]
        metrics = json.dumps(
            {
                "summary": True,
                "episodes_collapsed": len(oldest),
            },
            default=str,
        )

        self._delete_episode_ids(oldest_ids)
        self._conn.execute(
            "INSERT INTO episodes "
            "(id, session_id, sequence_num, started_at, ended_at, outcome, metrics) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                summary_episode_id,
                self._session_id,
                summary_sequence_num,
                summary_started_at,
                summary_ended_at,
                "summary",
                metrics,
            ),
        )
        self._conn.execute(
            "INSERT INTO episode_events (episode_id, event_type, timestamp, data) "
            "VALUES (?, ?, ?, ?)",
            (
                summary_episode_id,
                "summary",
                summary_ended_at,
                json.dumps(payload, default=str),
            ),
        )
        self._conn.commit()

    def _oldest_episodes(self, limit: int) -> list[tuple[str, int, str]]:
        rows = self._conn.execute(
            "SELECT id, sequence_num, started_at FROM episodes "
            "WHERE session_id = ? ORDER BY sequence_num ASC LIMIT ?",
            (self._session_id, limit),
        ).fetchall()
        return [(row[0], row[1], row[2]) for row in rows]

    def _events_for_episodes(self, episode_ids: list[str]) -> list[tuple[str, str]]:
        if not episode_ids:
            return []
        placeholders = ",".join("?" for _ in episode_ids)
        rows = self._conn.execute(
            "SELECT ee.event_type, ee.timestamp FROM episode_events ee "
            "JOIN episodes e ON e.id = ee.episode_id "
            f"WHERE ee.episode_id IN ({placeholders}) "
            "ORDER BY e.sequence_num ASC, ee.id ASC",
            episode_ids,
        ).fetchall()
        return [(row[0], row[1]) for row in rows]

    def _remaining_summary_ratio(self, excluding_episode_ids: list[str]) -> float:
        if excluding_episode_ids:
            placeholders = ",".join("?" for _ in excluding_episode_ids)
            rows = self._conn.execute(
                "SELECT ee.event_type FROM episode_events ee "
                "JOIN episodes e ON e.id = ee.episode_id "
                "WHERE e.session_id = ? "
                f"AND e.id NOT IN ({placeholders})",
                [self._session_id, *excluding_episode_ids],
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT ee.event_type FROM episode_events ee "
                "JOIN episodes e ON e.id = ee.episode_id "
                "WHERE e.session_id = ?",
                (self._session_id,),
            ).fetchall()
        if not rows:
            return 0.0
        summary_count = sum(1 for row in rows if row[0] == "summary")
        return summary_count / len(rows)

    def _summarize_tranche(self, events: list[tuple[str, str]]) -> dict:
        event_counts = Counter(event_type for event_type, _timestamp in events)
        timestamps = [timestamp for _event_type, timestamp in events]
        start = timestamps[0] if timestamps else _now_iso()
        end = timestamps[-1] if timestamps else start
        return {
            "event_counts": dict(event_counts),
            "ts_range": [start, end],
            "n_collapsed": len(events),
        }

    def _delete_oldest_summary_episode(self) -> bool:
        row = self._conn.execute(
            "SELECT e.id FROM episodes e "
            "JOIN episode_events ee ON ee.episode_id = e.id "
            "WHERE e.session_id = ? AND ee.event_type = 'summary' "
            "ORDER BY e.sequence_num ASC, ee.id ASC LIMIT 1",
            (self._session_id,),
        ).fetchone()
        if row is None:
            return False
        self._delete_episode_ids([row[0]])
        return True

    def _prune_until_next_episode_fits(self) -> None:
        while True:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM episodes WHERE session_id = ?",
                (self._session_id,),
            ).fetchone()
            if row[0] < self._max_episodes:
                return
            self._delete_oldest_episodes(1)

    def _delete_oldest_episodes(self, count: int) -> None:
        if count <= 0:
            return
        rows = self._oldest_episodes(count)
        self._delete_episode_ids([row[0] for row in rows])

    def _delete_episode_ids(self, episode_ids: list[str]) -> None:
        if not episode_ids:
            return
        placeholders = ",".join("?" for _ in episode_ids)
        self._conn.execute(
            f"DELETE FROM episode_events WHERE episode_id IN ({placeholders})",
            episode_ids,
        )
        self._conn.execute(
            f"DELETE FROM episodes WHERE id IN ({placeholders})",
            episode_ids,
        )
