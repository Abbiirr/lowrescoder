"""SQLite-backed session store with WAL mode."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from autocode.core.logging import log_event
from autocode.session.models import DDL, MessageRow, SessionRow, ensure_tables

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
        parent_session_id: str | None = None,
    ) -> str:
        """Create a new session, returning its UUID."""
        session_id = str(uuid.uuid4())
        now = _now_iso()
        self._conn.execute(
            "INSERT INTO sessions "
            "(id, title, model, provider, project_dir, parent_session_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (session_id, title, model, provider, project_dir, parent_session_id, now, now),
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

    def save_token_usage(self, session_id: str, snapshot: dict[str, object]) -> None:
        """Persist session-level token/cache counters."""
        now = _now_iso()
        per_provider = snapshot.get("per_provider") or {}
        self._conn.execute(
            """
            INSERT INTO session_token_usage (
                session_id,
                prompt_tokens,
                completion_tokens,
                cached_input_tokens,
                cache_creation_tokens,
                reasoning_tokens,
                call_count,
                per_provider_json,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                prompt_tokens = excluded.prompt_tokens,
                completion_tokens = excluded.completion_tokens,
                cached_input_tokens = excluded.cached_input_tokens,
                cache_creation_tokens = excluded.cache_creation_tokens,
                reasoning_tokens = excluded.reasoning_tokens,
                call_count = excluded.call_count,
                per_provider_json = excluded.per_provider_json,
                updated_at = excluded.updated_at
            """,
            (
                session_id,
                int(snapshot.get("prompt_tokens") or 0),
                int(snapshot.get("completion_tokens") or 0),
                int(snapshot.get("cached_input_tokens") or 0),
                int(snapshot.get("cache_creation_tokens") or 0),
                int(snapshot.get("reasoning_tokens") or 0),
                int(snapshot.get("call_count") or 0),
                json.dumps(per_provider),
                now,
            ),
        )
        self._conn.commit()

    def load_token_usage(self, session_id: str) -> dict[str, object]:
        """Load persisted session token/cache counters."""
        cursor = self._conn.execute(
            "SELECT * FROM session_token_usage WHERE session_id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return {}
        try:
            per_provider = json.loads(row["per_provider_json"])
        except json.JSONDecodeError:
            per_provider = {}
        return {
            "prompt_tokens": int(row["prompt_tokens"]),
            "completion_tokens": int(row["completion_tokens"]),
            "cached_input_tokens": int(row["cached_input_tokens"]),
            "cache_creation_tokens": int(row["cache_creation_tokens"]),
            "reasoning_tokens": int(row["reasoning_tokens"]),
            "call_count": int(row["call_count"]),
            "per_provider": per_provider if isinstance(per_provider, dict) else {},
        }

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

    def get_messages_with_tool_calls(self, session_id: str) -> list[dict[str, object]]:
        """Get chronological messages with assistant tool calls re-attached.

        The message table stores assistant content and tool results separately,
        while tool call metadata lives in the `tool_calls` table. Structured
        compaction and future context summaries need both views together.
        """
        messages = self.get_messages(session_id)
        if not messages:
            return []

        message_ids = [message.id for message in messages]
        placeholders = ",".join("?" for _ in message_ids)
        cursor = self._conn.execute(
            (
                "SELECT * FROM tool_calls WHERE session_id = ? "
                f"AND message_id IN ({placeholders}) "
                "ORDER BY created_at ASC, id ASC"
            ),
            (session_id, *message_ids),
        )

        tool_calls_by_message: dict[int, list[dict[str, object]]] = {}
        for row in cursor.fetchall():
            arguments: object
            raw_arguments = row["arguments"]
            try:
                arguments = (
                    json.loads(raw_arguments)
                    if isinstance(raw_arguments, str)
                    else raw_arguments
                )
            except json.JSONDecodeError:
                arguments = {}
            if not isinstance(arguments, dict):
                arguments = {}

            tool_calls_by_message.setdefault(row["message_id"], []).append({
                "id": row["tool_call_id"],
                "type": "function",
                "function": {
                    "name": row["tool_name"],
                    "arguments": arguments,
                },
            })

        conversation: list[dict[str, object]] = []
        for message in messages:
            entry: dict[str, object] = {
                "role": message.role,
                "content": message.content,
            }
            tool_calls = tool_calls_by_message.get(message.id)
            if tool_calls:
                entry["tool_calls"] = tool_calls
            conversation.append(entry)

        return conversation

    def snapshot_messages(
        self,
        session_id: str,
        limit: int = 20,
    ) -> list[dict[str, object]]:
        """Return a bounded message snapshot with tool-call rows attached."""
        safe_limit = max(limit, 0)
        cursor = self._conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC, id ASC",
            (session_id,),
        )
        rows = cursor.fetchall()
        selected = rows[-safe_limit:] if safe_limit else []
        if not selected:
            return []

        message_ids = [int(row["id"]) for row in selected]
        placeholders = ",".join("?" for _ in message_ids)
        cursor = self._conn.execute(
            (
                "SELECT * FROM tool_calls WHERE session_id = ? "
                f"AND message_id IN ({placeholders}) "
                "ORDER BY created_at ASC, id ASC"
            ),
            (session_id, *message_ids),
        )

        tool_calls_by_message: dict[int, list[dict[str, object]]] = {}
        for row in cursor.fetchall():
            tool_calls_by_message.setdefault(int(row["message_id"]), []).append({
                "tool_call_id": row["tool_call_id"],
                "tool_name": row["tool_name"],
                "arguments": row["arguments"],
                "result": row["result"],
                "status": row["status"],
                "duration_ms": row["duration_ms"],
                "created_at": row["created_at"],
            })

        messages: list[dict[str, object]] = []
        for row in selected:
            entry: dict[str, object] = {
                "role": row["role"],
                "content": row["content"],
                "token_count": row["token_count"],
                "created_at": row["created_at"],
            }
            tool_calls = tool_calls_by_message.get(int(row["id"]))
            if tool_calls:
                entry["tool_calls"] = tool_calls
            messages.append(entry)
        return messages

    def restore_messages_snapshot(
        self,
        session_id: str,
        messages: list[dict[str, object]],
        *,
        autocommit: bool = True,
    ) -> None:
        """Replace a session's messages/tool calls from a checkpoint snapshot."""
        self._conn.execute("DELETE FROM tool_calls WHERE session_id = ?", (session_id,))
        self._conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))

        for message in messages:
            cursor = self._conn.execute(
                "INSERT INTO messages "
                "(session_id, role, content, token_count, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    session_id,
                    str(message.get("role", "user")),
                    str(message.get("content", "")),
                    int(message.get("token_count") or 0),
                    str(message.get("created_at") or _now_iso()),
                ),
            )
            message_id = cursor.lastrowid or 0
            tool_calls = message.get("tool_calls", [])
            if not isinstance(tool_calls, list):
                continue
            for tool_call in tool_calls:
                if not isinstance(tool_call, dict):
                    continue
                arguments = tool_call.get("arguments", "{}")
                if not isinstance(arguments, str):
                    arguments = json.dumps(arguments)
                self._conn.execute(
                    "INSERT INTO tool_calls "
                    "(session_id, message_id, tool_call_id, tool_name, arguments, "
                    "result, status, duration_ms, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        session_id,
                        message_id,
                        str(tool_call.get("tool_call_id", "")),
                        str(tool_call.get("tool_name", "")),
                        arguments,
                        tool_call.get("result"),
                        str(tool_call.get("status", "pending")),
                        tool_call.get("duration_ms"),
                        str(tool_call.get("created_at") or _now_iso()),
                    ),
                )

        if autocommit:
            self._conn.commit()

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
