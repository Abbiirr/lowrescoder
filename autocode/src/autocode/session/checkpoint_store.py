"""Checkpoint store: save and restore task state snapshots.

Checkpoints capture the full task DAG state at a point in time,
enabling transactional rollback of task state along with a context
summary injected into the session history.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

from autocode.session.models import CheckpointRow

logger = logging.getLogger(__name__)

DEFAULT_MESSAGE_LIMIT = 20
EMPTY_MESSAGE_SNAPSHOT = {"captured": False, "summary": "", "messages": []}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _decode_message_snapshot(raw: str) -> dict[str, Any]:
    """Decode a checkpoint message snapshot, tolerating older checkpoint rows."""
    try:
        snapshot = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return dict(EMPTY_MESSAGE_SNAPSHOT)
    if not isinstance(snapshot, dict):
        return dict(EMPTY_MESSAGE_SNAPSHOT)
    snapshot.setdefault("captured", False)
    snapshot.setdefault("summary", "")
    snapshot.setdefault("messages", [])
    if not isinstance(snapshot["messages"], list):
        snapshot["messages"] = []
    return snapshot


class CheckpointStore:
    """CRUD operations for checkpoints in SQLite.

    Follows TaskStore pattern: takes a connection and session_id.
    """

    def __init__(self, conn: sqlite3.Connection, session_id: str) -> None:
        self._conn = conn
        self._session_id = session_id

    def save_checkpoint(
        self,
        task_store: Any,
        label: str,
        context_summary: str = "",
        active_files: list[str] | None = None,
        session_store: Any | None = None,
        message_limit: int = DEFAULT_MESSAGE_LIMIT,
    ) -> str:
        """Serialize task state as JSON snapshot, returns checkpoint ID."""
        checkpoint_id = uuid.uuid4().hex[:12]
        now = _now_iso()
        tasks_snapshot = json.dumps(task_store.snapshot())
        messages_snapshot = json.dumps(
            self._build_message_snapshot(session_store, context_summary, message_limit)
        )
        files_json = json.dumps(active_files or [])

        self._conn.execute(
            "INSERT INTO checkpoints "
            "(id, session_id, label, tasks_snapshot, messages_snapshot, "
            "context_summary, active_files, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                checkpoint_id,
                self._session_id,
                label,
                tasks_snapshot,
                messages_snapshot,
                context_summary,
                files_json,
                now,
            ),
        )
        self._conn.commit()
        logger.info("Checkpoint saved: %s (%s)", checkpoint_id, label)
        return checkpoint_id

    def _build_message_snapshot(
        self,
        session_store: Any | None,
        context_summary: str,
        message_limit: int,
    ) -> dict[str, Any]:
        """Build the bounded message-history snapshot for this checkpoint."""
        if session_store is None:
            return {
                "captured": False,
                "summary": context_summary,
                "messages": [],
            }
        if not hasattr(session_store, "snapshot_messages"):
            raise TypeError("session_store must provide snapshot_messages()")
        return {
            "captured": True,
            "summary": context_summary,
            "messages": session_store.snapshot_messages(
                self._session_id,
                limit=message_limit,
            ),
        }

    def list_checkpoints(self) -> list[CheckpointRow]:
        """List checkpoints for this session, newest first."""
        cursor = self._conn.execute(
            "SELECT * FROM checkpoints WHERE session_id = ? ORDER BY created_at DESC",
            (self._session_id,),
        )
        return [CheckpointRow(**dict(row)) for row in cursor.fetchall()]

    def get_checkpoint(self, checkpoint_id: str) -> CheckpointRow | None:
        """Get a single checkpoint by exact ID or unique prefix."""
        cursor = self._conn.execute(
            "SELECT * FROM checkpoints WHERE id = ? AND session_id = ?",
            (checkpoint_id, self._session_id),
        )
        row = cursor.fetchone()
        if row is not None:
            return CheckpointRow(**dict(row))
        # Prefix match fallback
        cursor = self._conn.execute(
            "SELECT * FROM checkpoints WHERE id LIKE ? AND session_id = ?",
            (checkpoint_id + "%", self._session_id),
        )
        rows = cursor.fetchall()
        if len(rows) == 1:
            return CheckpointRow(**dict(rows[0]))
        return None

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint. Returns True if deleted."""
        cursor = self._conn.execute(
            "DELETE FROM checkpoints WHERE id = ? AND session_id = ?",
            (checkpoint_id, self._session_id),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def restore_checkpoint(
        self,
        checkpoint_id: str,
        task_store: Any,
        session_store: Any,
    ) -> dict[str, Any]:
        """Transactional restore: rehydrate tasks and inject context summary.

        Uses BEGIN IMMEDIATE to wrap the restore in a single transaction.
        Both task_store.restore_from_snapshot() and session_store.add_message()
        are called with autocommit=False so this method controls the commit.

        Returns dict with label and active_files for the caller.
        Raises ValueError if the checkpoint belongs to a different session.
        """
        cp = self.get_checkpoint(checkpoint_id)
        if cp is None:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")
        if cp.session_id != self._session_id:
            raise ValueError(
                f"Session mismatch: checkpoint={cp.session_id}, current={self._session_id}"
            )

        conn = self._conn
        restored_messages = 0
        restored_tool_calls = 0

        try:
            conn.execute("BEGIN IMMEDIATE")
            task_store.restore_from_snapshot(
                json.loads(cp.tasks_snapshot), autocommit=False,
            )
            message_snapshot = _decode_message_snapshot(cp.messages_snapshot)
            if message_snapshot.get("captured"):
                if not hasattr(session_store, "restore_messages_snapshot"):
                    raise TypeError("session_store must provide restore_messages_snapshot()")
                restored_messages = len(message_snapshot["messages"])
                restored_tool_calls = sum(
                    len(message.get("tool_calls", []))
                    for message in message_snapshot["messages"]
                    if isinstance(message, dict)
                    and isinstance(message.get("tool_calls", []), list)
                )
                session_store.restore_messages_snapshot(
                    cp.session_id,
                    message_snapshot["messages"],
                    autocommit=False,
                )
            session_store.add_message(
                cp.session_id, "system",
                f"[Restored checkpoint: {cp.label}]\n{cp.context_summary}",
                autocommit=False,
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

        logger.info("Checkpoint restored: %s (%s)", checkpoint_id, cp.label)
        return {
            "checkpoint_id": cp.id,
            "label": cp.label,
            "active_files": json.loads(cp.active_files),
            "restored_messages": restored_messages,
            "restored_tool_calls": restored_tool_calls,
        }
