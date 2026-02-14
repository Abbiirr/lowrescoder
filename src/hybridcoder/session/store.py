"""SQLite-backed session store with WAL mode."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from hybridcoder.core.logging import log_event
from hybridcoder.session.models import DDL, MessageRow, SessionRow, ensure_tables

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class SessionStore:
    """Persistent session storage using SQLite."""

    def __init__(self, db_path: str | Path) -> None:
        path = Path(db_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = path
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(DDL)
        ensure_tables(self._conn)  # idempotent, ensures task tables exist

    def get_connection(self) -> sqlite3.Connection:
        """Return the underlying SQLite connection."""
        return self._conn

    def close(self) -> None:
        self._conn.close()

    # --- Sessions ---

    def create_session(
        self,
        title: str,
        model: str,
        provider: str,
        project_dir: str = "",
    ) -> str:
        """Create a new session, returning its UUID."""
        session_id = str(uuid.uuid4())
        now = _now_iso()
        self._conn.execute(
            "INSERT INTO sessions "
            "(id, title, model, provider, project_dir, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, title, model, provider, project_dir, now, now),
        )
        self._conn.commit()
        log_event(
            logger, logging.INFO, "session_created",
            session_id=session_id, model=model, provider=provider,
        )
        return session_id

    def list_sessions(self) -> list[SessionRow]:
        """List all sessions ordered by most recent first."""
        cursor = self._conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC")
        return [SessionRow(**dict(row)) for row in cursor.fetchall()]

    def get_session(self, session_id: str) -> SessionRow | None:
        """Get a single session by ID."""
        cursor = self._conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        return SessionRow(**dict(row)) if row else None

    def update_session(self, session_id: str, **kwargs: object) -> None:
        """Update session fields (title, summary, token_count, updated_at)."""
        kwargs["updated_at"] = _now_iso()
        allowed = {"title", "summary", "token_count", "updated_at"}
        filtered = {k: v for k, v in kwargs.items() if k in allowed}
        if not filtered:
            return
        set_clause = ", ".join(f"{k} = ?" for k in filtered)
        values = list(filtered.values()) + [session_id]
        self._conn.execute(
            f"UPDATE sessions SET {set_clause} WHERE id = ?",  # noqa: S608
            values,
        )
        self._conn.commit()

    # --- Messages ---

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        token_count: int = 0,
        *,
        autocommit: bool = True,
    ) -> int:
        """Add a message to a session, returning its row ID.

        When autocommit=False, the caller controls the transaction boundary
        (used by CheckpointStore for transactional restore).
        """
        now = _now_iso()
        cursor = self._conn.execute(
            "INSERT INTO messages (session_id, role, content, token_count, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, token_count, now),
        )
        if autocommit:
            self._conn.commit()
        return cursor.lastrowid or 0

    def get_messages(self, session_id: str) -> list[MessageRow]:
        """Get all messages for a session in chronological order."""
        cursor = self._conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC, id ASC",
            (session_id,),
        )
        return [MessageRow(**dict(row)) for row in cursor.fetchall()]

    # --- Tool calls ---

    def add_tool_call(
        self,
        session_id: str,
        message_id: int,
        tool_call_id: str,
        tool_name: str,
        arguments: str | dict[str, object] = "{}",
        status: str = "pending",
    ) -> int:
        """Add a tool call record, returning its row ID."""
        if isinstance(arguments, dict):
            arguments = json.dumps(arguments)
        now = _now_iso()
        cursor = self._conn.execute(
            "INSERT INTO tool_calls "
            "(session_id, message_id, tool_call_id, tool_name, arguments, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, message_id, tool_call_id, tool_name, arguments, status, now),
        )
        self._conn.commit()
        return cursor.lastrowid or 0

    def update_tool_call(
        self,
        tool_call_row_id: int,
        result: str,
        status: str = "completed",
        duration_ms: int | None = None,
    ) -> None:
        """Update a tool call with its result."""
        self._conn.execute(
            "UPDATE tool_calls SET result = ?, status = ?, duration_ms = ? WHERE id = ?",
            (result, status, duration_ms, tool_call_row_id),
        )
        self._conn.commit()

    # --- Compaction ---

    def compact_session(
        self,
        session_id: str,
        summary: str,
        kept_messages: int = 4,
    ) -> None:
        """Replace old messages with a summary, keeping only recent messages."""
        messages = self.get_messages(session_id)
        if len(messages) <= kept_messages:
            return

        # Delete old messages (keep the last `kept_messages`)
        cutoff_id = messages[-kept_messages].id
        self._conn.execute(
            "DELETE FROM tool_calls WHERE session_id = ? AND message_id < ?",
            (session_id, cutoff_id),
        )
        self._conn.execute(
            "DELETE FROM messages WHERE session_id = ? AND id < ?",
            (session_id, cutoff_id),
        )

        # Insert summary as a system message that sorts before kept messages
        # Use epoch timestamp so it always appears first in chronological order
        self._conn.execute(
            "INSERT INTO messages (session_id, role, content, token_count, created_at) "
            "VALUES (?, 'system', ?, 0, '1970-01-01T00:00:00+00:00')",
            (session_id, summary),
        )

        # Update session summary
        self.update_session(session_id, summary=summary)
        self._conn.commit()
