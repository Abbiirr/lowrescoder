"""Episode store for training-grade event logging."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
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
        """Delete oldest episodes (and their events) beyond max_episodes_per_session."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM episodes WHERE session_id = ?",
            (self._session_id,),
        ).fetchone()
        count = row[0]
        if count < self._max_episodes:
            return

        excess = count - self._max_episodes + 1  # +1 to make room for the new one
        oldest = self._conn.execute(
            "SELECT id FROM episodes WHERE session_id = ? ORDER BY sequence_num ASC LIMIT ?",
            (self._session_id, excess),
        ).fetchall()
        for (eid,) in oldest:
            self._conn.execute(
                "DELETE FROM episode_events WHERE episode_id = ?", (eid,),
            )
            self._conn.execute(
                "DELETE FROM episodes WHERE id = ?", (eid,),
            )
        self._conn.commit()
