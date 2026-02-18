"""Tests for session store SQLite persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from autocode.session.store import SessionStore


@pytest.fixture()
def store(tmp_path: Path) -> SessionStore:
    """Create a fresh session store for each test."""
    s = SessionStore(tmp_path / "test_sessions.db")
    yield s
    s.close()


class TestSessionStore:
    def test_create_and_get_session(self, store: SessionStore) -> None:
        sid = store.create_session(
            title="Test", model="qwen3:8b", provider="ollama", project_dir="/tmp"
        )
        assert isinstance(sid, str)
        assert len(sid) == 36  # UUID format

        session = store.get_session(sid)
        assert session is not None
        assert session.title == "Test"
        assert session.model == "qwen3:8b"
        assert session.provider == "ollama"

    def test_list_sessions(self, store: SessionStore) -> None:
        store.create_session(title="First", model="m1", provider="ollama")
        store.create_session(title="Second", model="m2", provider="ollama")

        sessions = store.list_sessions()
        assert len(sessions) == 2
        titles = {s.title for s in sessions}
        assert titles == {"First", "Second"}

    def test_add_and_get_messages(self, store: SessionStore) -> None:
        sid = store.create_session(title="Chat", model="m", provider="ollama")
        mid1 = store.add_message(sid, "user", "Hello", token_count=2)
        mid2 = store.add_message(sid, "assistant", "Hi there!", token_count=3)

        assert mid1 > 0
        assert mid2 > mid1

        messages = store.get_messages(sid)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Hello"
        assert messages[1].role == "assistant"
        assert messages[1].content == "Hi there!"

    def test_add_and_update_tool_call(self, store: SessionStore) -> None:
        sid = store.create_session(title="Tools", model="m", provider="ollama")
        mid = store.add_message(sid, "assistant", "calling tool")

        tc_id = store.add_tool_call(
            session_id=sid,
            message_id=mid,
            tool_call_id="tc_001",
            tool_name="read_file",
            arguments={"path": "test.py"},
            status="pending",
        )
        assert tc_id > 0

        store.update_tool_call(
            tc_id, result="file contents here", status="completed", duration_ms=42,
        )

        # Verify via raw query
        cursor = store._conn.execute("SELECT * FROM tool_calls WHERE id = ?", (tc_id,))
        row = dict(cursor.fetchone())
        assert row["status"] == "completed"
        assert row["result"] == "file contents here"
        assert row["duration_ms"] == 42

    def test_compact_session(self, store: SessionStore) -> None:
        sid = store.create_session(title="Long chat", model="m", provider="ollama")
        for i in range(10):
            store.add_message(sid, "user", f"msg {i}")
            store.add_message(sid, "assistant", f"reply {i}")

        assert len(store.get_messages(sid)) == 20

        store.compact_session(sid, summary="Summary of conversation", kept_messages=4)

        messages = store.get_messages(sid)
        # Should have: summary system message + 4 kept messages = 5
        assert len(messages) == 5
        # First message should be the summary
        assert messages[0].role == "system"
        assert "Summary" in messages[0].content

        # Session should have the summary
        session = store.get_session(sid)
        assert session is not None
        assert session.summary == "Summary of conversation"

    def test_session_db_wal_mode(self, store: SessionStore) -> None:
        cursor = store._conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode == "wal"
