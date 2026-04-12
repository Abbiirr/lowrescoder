"""Tests for MessageStore — persistent mailbox with ack/claim/lease."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone, timedelta

import pytest

from autocode.agent.bus import AgentBus, AgentMessage, MessageType
from autocode.agent.events import NullEventSink, SqliteEventSink
from autocode.agent.message_store import (
    MessageStatus,
    MessageStore,
    MessageStoreAdapter,
)
from autocode.session.models import ensure_tables


@pytest.fixture()
def conn():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    ensure_tables(db)
    return db


@pytest.fixture()
def store(conn: sqlite3.Connection) -> MessageStore:
    return MessageStore(conn, session_id="test-session")


@pytest.fixture()
def store_with_events(conn: sqlite3.Connection) -> MessageStore:
    sink = SqliteEventSink(conn)
    return MessageStore(conn, session_id="test-session", event_sink=sink)


# ── MessageStatus ──


class TestMessageStatus:
    def test_status_values(self) -> None:
        assert MessageStatus.PENDING == "pending"
        assert MessageStatus.CLAIMED == "claimed"
        assert MessageStatus.PROCESSED == "processed"
        assert MessageStatus.FAILED == "failed"


# ── Send / Receive ──


class TestMessageStoreSendReceive:
    def test_send_persists_to_sqlite(self, store: MessageStore, conn: sqlite3.Connection) -> None:
        msg = AgentMessage(
            from_agent="lead",
            to_agent="worker",
            message_type=MessageType.REQUEST,
            payload={"task": "fix bug"},
            task_id="t1",
        )
        mid = store.send(msg)
        assert mid == msg.id

        cursor = conn.execute(
            "SELECT * FROM agent_mailbox WHERE message_id = ?", (mid,),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row["from_agent"] == "lead"
        assert row["to_agent"] == "worker"
        assert row["status"] == "pending"

    def test_send_emits_event(self, store_with_events: MessageStore, conn: sqlite3.Connection) -> None:
        msg = AgentMessage(from_agent="lead", to_agent="worker")
        store_with_events.send(msg)

        cursor = conn.execute(
            "SELECT * FROM orchestrator_events WHERE event_type = 'message_sent'",
        )
        assert cursor.fetchone() is not None

    def test_count(self, store: MessageStore) -> None:
        store.send(AgentMessage(from_agent="a", to_agent="b"))
        store.send(AgentMessage(from_agent="a", to_agent="c"))
        assert store.count() == 2
        assert store.count(agent_id="b") == 1


# ── Claim ──


class TestMessageStoreClaim:
    def test_claim_pending_message(self, store: MessageStore) -> None:
        msg = AgentMessage(from_agent="lead", to_agent="worker")
        mid = store.send(msg)
        assert store.claim(mid, "worker", lease_seconds=60)

    def test_claim_already_claimed_fails(self, store: MessageStore) -> None:
        msg = AgentMessage(from_agent="lead", to_agent="worker")
        mid = store.send(msg)
        store.claim(mid, "worker")
        assert not store.claim(mid, "other-worker")

    def test_claim_sets_lease(self, store: MessageStore, conn: sqlite3.Connection) -> None:
        msg = AgentMessage(from_agent="lead", to_agent="worker")
        mid = store.send(msg)
        store.claim(mid, "worker", lease_seconds=120)

        cursor = conn.execute(
            "SELECT claimed_by, claim_until, status FROM agent_mailbox WHERE message_id = ?",
            (mid,),
        )
        row = cursor.fetchone()
        assert row["claimed_by"] == "worker"
        assert row["claim_until"] is not None
        assert row["status"] == "claimed"

    def test_claim_nonexistent_message_fails(self, store: MessageStore) -> None:
        assert not store.claim("nonexistent", "worker")


# ── Ack / Nack ──


class TestMessageStoreAck:
    def test_ack_sets_processed(self, store: MessageStore, conn: sqlite3.Connection) -> None:
        msg = AgentMessage(from_agent="lead", to_agent="worker")
        mid = store.send(msg)
        store.claim(mid, "worker")
        store.ack(mid)

        cursor = conn.execute(
            "SELECT status FROM agent_mailbox WHERE message_id = ?", (mid,),
        )
        assert cursor.fetchone()["status"] == "processed"

    def test_nack_sets_failed(self, store: MessageStore, conn: sqlite3.Connection) -> None:
        msg = AgentMessage(from_agent="lead", to_agent="worker")
        mid = store.send(msg)
        store.claim(mid, "worker")
        store.nack(mid)

        cursor = conn.execute(
            "SELECT status FROM agent_mailbox WHERE message_id = ?", (mid,),
        )
        assert cursor.fetchone()["status"] == "failed"


# ── Inbox / Outbox ──


class TestMessageStoreInboxOutbox:
    def test_get_inbox_filters_by_agent(self, store: MessageStore) -> None:
        store.send(AgentMessage(from_agent="lead", to_agent="worker-1", task_id="t1"))
        store.send(AgentMessage(from_agent="lead", to_agent="worker-2", task_id="t1"))
        inbox = store.get_inbox("worker-1")
        assert len(inbox) == 1
        assert inbox[0].to_agent == "worker-1"

    def test_get_inbox_filters_by_status(self, store: MessageStore) -> None:
        msg = AgentMessage(from_agent="lead", to_agent="worker")
        mid = store.send(msg)
        store.claim(mid, "worker")

        pending = store.get_inbox("worker", status=MessageStatus.PENDING)
        assert len(pending) == 0

        claimed = store.get_inbox("worker", status=MessageStatus.CLAIMED)
        assert len(claimed) == 1

    def test_get_outbox_returns_sent(self, store: MessageStore) -> None:
        store.send(AgentMessage(from_agent="lead", to_agent="worker-1"))
        store.send(AgentMessage(from_agent="lead", to_agent="worker-2"))
        store.send(AgentMessage(from_agent="other", to_agent="worker-1"))
        outbox = store.get_outbox("lead")
        assert len(outbox) == 2

    def test_get_thread(self, store: MessageStore) -> None:
        store.send(AgentMessage(from_agent="a", to_agent="b", task_id="t1"))
        store.send(AgentMessage(from_agent="b", to_agent="a", task_id="t1"))
        store.send(AgentMessage(from_agent="a", to_agent="c", task_id="t2"))
        thread = store.get_thread("t1")
        assert len(thread) == 2


# ── Lease Expiry ──


class TestMessageStoreLeaseExpiry:
    def test_release_expired_claims(self, store: MessageStore, conn: sqlite3.Connection) -> None:
        msg = AgentMessage(from_agent="lead", to_agent="worker")
        mid = store.send(msg)
        store.claim(mid, "worker", lease_seconds=1)

        # Manually set claim_until to the past
        past = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        conn.execute(
            "UPDATE agent_mailbox SET claim_until = ? WHERE message_id = ?",
            (past, mid),
        )
        conn.commit()

        released = store.release_expired_claims()
        assert released == 1

        cursor = conn.execute(
            "SELECT status, claimed_by FROM agent_mailbox WHERE message_id = ?",
            (mid,),
        )
        row = cursor.fetchone()
        assert row["status"] == "pending"
        assert row["claimed_by"] is None

    def test_unexpired_claims_not_released(self, store: MessageStore) -> None:
        msg = AgentMessage(from_agent="lead", to_agent="worker")
        mid = store.send(msg)
        store.claim(mid, "worker", lease_seconds=3600)  # 1 hour
        assert store.release_expired_claims() == 0


# ── Restart / Recovery ──


class TestMessageStoreRestartRecovery:
    def test_messages_survive_reconnect(self) -> None:
        """Messages persist across SQLite connection close/reopen."""
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            # First connection: create and send
            conn1 = sqlite3.connect(db_path)
            conn1.row_factory = sqlite3.Row
            ensure_tables(conn1)
            store1 = MessageStore(conn1, session_id="s1")
            store1.send(AgentMessage(from_agent="a", to_agent="b", task_id="t1"))
            store1.send(AgentMessage(from_agent="a", to_agent="b", task_id="t1"))
            conn1.close()

            # Second connection: verify
            conn2 = sqlite3.connect(db_path)
            conn2.row_factory = sqlite3.Row
            ensure_tables(conn2)
            store2 = MessageStore(conn2, session_id="s1")
            inbox = store2.get_inbox("b")
            assert len(inbox) == 2
            conn2.close()
        finally:
            os.unlink(db_path)

    def test_claimed_state_survives_reconnect(self) -> None:
        """Claimed messages retain their status after restart."""
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            conn1 = sqlite3.connect(db_path)
            conn1.row_factory = sqlite3.Row
            ensure_tables(conn1)
            store1 = MessageStore(conn1, session_id="s1")
            msg = AgentMessage(from_agent="a", to_agent="b")
            mid = store1.send(msg)
            store1.claim(mid, "b")
            conn1.close()

            conn2 = sqlite3.connect(db_path)
            conn2.row_factory = sqlite3.Row
            ensure_tables(conn2)
            store2 = MessageStore(conn2, session_id="s1")
            pending = store2.get_inbox("b", status=MessageStatus.PENDING)
            claimed = store2.get_inbox("b", status=MessageStatus.CLAIMED)
            assert len(pending) == 0
            assert len(claimed) == 1
            conn2.close()
        finally:
            os.unlink(db_path)


# ── MessageStoreAdapter ──


class TestMessageStoreAdapter:
    def test_adapter_persists_and_notifies(self, store: MessageStore) -> None:
        bus = AgentBus()
        adapter = MessageStoreAdapter(store, bus)

        received: list[AgentMessage] = []
        bus.subscribe("worker", lambda m: received.append(m))

        msg = AgentMessage(from_agent="lead", to_agent="worker", task_id="t1")
        adapter.send(msg)

        # Persisted
        assert store.count() == 1
        # Notified
        assert len(received) == 1

    def test_adapter_bus_get_pending_works(self, store: MessageStore) -> None:
        bus = AgentBus()
        adapter = MessageStoreAdapter(store, bus)
        adapter.send(AgentMessage(from_agent="lead", to_agent="worker"))

        # Bus should also have the message for backward compat
        pending = bus.get_pending("worker")
        assert len(pending) == 1
