"""MessageStore — persistent mailbox with ack/claim/lease semantics.

This is NOT a subclass of AgentBus. AgentBus remains the in-memory pub/sub
primitive. MessageStore is a durable message store with delivery guarantees.
MessageStoreAdapter bridges the two when both are needed.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import UTC, datetime, timedelta

from autocode.agent.bus import AgentBus, AgentMessage, MessageStatus, MessageType
from autocode.agent.events import EventSink, EventType, NullEventSink, OrchestratorEvent

logger = logging.getLogger(__name__)


class MessageStore:
    """SQLite-backed persistent mailbox with ack/claim/lease semantics."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        session_id: str,
        event_sink: EventSink | None = None,
    ) -> None:
        self._conn = conn
        self._session_id = session_id
        self._event_sink = event_sink or NullEventSink()

    def send(self, message: AgentMessage) -> str:
        """Persist a message. Returns message ID. Emits MESSAGE_SENT event."""
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            "INSERT INTO agent_mailbox "
            "(message_id, session_id, from_agent, to_agent, message_type, "
            " status, payload, task_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                message.id,
                self._session_id,
                message.from_agent,
                message.to_agent,
                message.message_type.value,
                MessageStatus.PENDING.value,
                json.dumps(message.payload, default=str),
                message.task_id,
                now,
                now,
            ),
        )
        self._conn.commit()

        self._event_sink.emit(OrchestratorEvent(
            event_type=EventType.MESSAGE_SENT,
            session_id=self._session_id,
            task_id=message.task_id or "",
            source_agent=message.from_agent,
            payload={
                "message_id": message.id,
                "to_agent": message.to_agent or "",
                "message_type": message.message_type.value,
            },
        ))

        return message.id

    def claim(
        self,
        message_id: str,
        agent_id: str,
        lease_seconds: int = 60,
    ) -> bool:
        """Claim a pending message with a lease. Returns True if claimed."""
        claim_until = (
            datetime.now(UTC) + timedelta(seconds=lease_seconds)
        ).isoformat()
        now = datetime.now(UTC).isoformat()

        cursor = self._conn.execute(
            "UPDATE agent_mailbox SET status = ?, claimed_by = ?, "
            "claim_until = ?, updated_at = ? "
            "WHERE message_id = ? AND session_id = ? AND status = ?",
            (
                MessageStatus.CLAIMED.value,
                agent_id,
                claim_until,
                now,
                message_id,
                self._session_id,
                MessageStatus.PENDING.value,
            ),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def ack(self, message_id: str) -> None:
        """Acknowledge processing complete. Sets status to PROCESSED."""
        self._update_status(message_id, MessageStatus.PROCESSED)

    def nack(self, message_id: str) -> None:
        """Negative ack. Sets status to FAILED."""
        self._update_status(message_id, MessageStatus.FAILED)

    def get_inbox(
        self,
        agent_id: str,
        status: MessageStatus | None = None,
    ) -> list[AgentMessage]:
        """Get messages addressed to agent_id, optionally filtered by status."""
        if status:
            cursor = self._conn.execute(
                "SELECT * FROM agent_mailbox "
                "WHERE to_agent = ? AND session_id = ? AND status = ? "
                "ORDER BY created_at ASC",
                (agent_id, self._session_id, status.value),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM agent_mailbox "
                "WHERE to_agent = ? AND session_id = ? "
                "ORDER BY created_at ASC",
                (agent_id, self._session_id),
            )
        return [self._row_to_message(row) for row in cursor.fetchall()]

    def get_outbox(self, agent_id: str) -> list[AgentMessage]:
        """Get messages sent by agent_id."""
        cursor = self._conn.execute(
            "SELECT * FROM agent_mailbox "
            "WHERE from_agent = ? AND session_id = ? "
            "ORDER BY created_at ASC",
            (agent_id, self._session_id),
        )
        return [self._row_to_message(row) for row in cursor.fetchall()]

    def get_thread(self, task_id: str) -> list[AgentMessage]:
        """Get all messages for a task, ordered by timestamp."""
        cursor = self._conn.execute(
            "SELECT * FROM agent_mailbox "
            "WHERE task_id = ? AND session_id = ? "
            "ORDER BY created_at ASC",
            (task_id, self._session_id),
        )
        return [self._row_to_message(row) for row in cursor.fetchall()]

    def release_expired_claims(self) -> int:
        """Release messages with expired claim_until back to PENDING."""
        now = datetime.now(UTC).isoformat()
        cursor = self._conn.execute(
            "UPDATE agent_mailbox SET status = ?, claimed_by = NULL, "
            "claim_until = NULL, updated_at = ? "
            "WHERE status = ? AND claim_until < ? AND session_id = ?",
            (
                MessageStatus.PENDING.value,
                now,
                MessageStatus.CLAIMED.value,
                now,
                self._session_id,
            ),
        )
        self._conn.commit()
        return cursor.rowcount

    def count(
        self,
        agent_id: str = "",
        status: MessageStatus | None = None,
    ) -> int:
        """Count messages with optional filters."""
        conditions = ["session_id = ?"]
        params: list[str] = [self._session_id]

        if agent_id:
            conditions.append("to_agent = ?")
            params.append(agent_id)
        if status:
            conditions.append("status = ?")
            params.append(status.value)

        where = " AND ".join(conditions)
        cursor = self._conn.execute(
            f"SELECT COUNT(*) FROM agent_mailbox WHERE {where}",  # noqa: S608
            params,
        )
        return cursor.fetchone()[0]

    def _update_status(self, message_id: str, status: MessageStatus) -> None:
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            "UPDATE agent_mailbox SET status = ?, updated_at = ? "
            "WHERE message_id = ? AND session_id = ?",
            (status.value, now, message_id, self._session_id),
        )
        self._conn.commit()

    @staticmethod
    def _row_to_message(row: sqlite3.Row) -> AgentMessage:
        payload = json.loads(row["payload"]) if row["payload"] else {}
        return AgentMessage(
            id=row["message_id"],
            from_agent=row["from_agent"],
            to_agent=row["to_agent"],
            message_type=MessageType(row["message_type"]),
            payload=payload,
            task_id=row["task_id"],
        )


class MessageStoreAdapter:
    """Bridges MessageStore and AgentBus for backward compatibility.

    send() persists to MessageStore AND forwards to AgentBus (which
    notifies in-memory subscribers and maintains get_pending/get_thread).
    """

    def __init__(self, store: MessageStore, bus: AgentBus) -> None:
        self._store = store
        self._bus = bus

    def send(self, message: AgentMessage) -> str:
        """Persist and notify. Returns message ID."""
        mid = self._store.send(message)
        self._bus.send(message)
        return mid
