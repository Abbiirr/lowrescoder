"""Tests for CheckpointStore (Sprint 4C)."""

from __future__ import annotations

import sqlite3

import pytest

from hybridcoder.session.checkpoint_store import CheckpointStore
from hybridcoder.session.models import ensure_tables
from hybridcoder.session.task_store import TaskStore


@pytest.fixture()
def setup():
    """In-memory SQLite with session, tasks, and checkpoint stores."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_tables(conn)

    # Create a session directly
    conn.execute(
        "INSERT INTO sessions (id, title, model, provider, project_dir, created_at, updated_at) "
        "VALUES ('sess-1', 'Test', 'test', 'test', '.', '2024-01-01', '2024-01-01')"
    )
    conn.commit()

    task_store = TaskStore(conn, "sess-1")
    cp_store = CheckpointStore(conn, "sess-1")
    return conn, task_store, cp_store


class TestCheckpointStore:
    """7 tests for CheckpointStore."""

    def test_save_checkpoint(self, setup) -> None:
        """Save a checkpoint and verify it exists."""
        conn, task_store, cp_store = setup
        task_store.create_task("Task A")
        cp_id = cp_store.save_checkpoint(task_store, "before refactor")
        assert cp_id
        checkpoints = cp_store.list_checkpoints()
        assert len(checkpoints) == 1
        assert checkpoints[0].label == "before refactor"

    def test_list_checkpoints(self, setup) -> None:
        """List checkpoints returns all entries."""
        conn, task_store, cp_store = setup
        cp_store.save_checkpoint(task_store, "first")
        cp_store.save_checkpoint(task_store, "second")
        checkpoints = cp_store.list_checkpoints()
        assert len(checkpoints) == 2
        labels = {cp.label for cp in checkpoints}
        assert labels == {"first", "second"}

    def test_delete_checkpoint(self, setup) -> None:
        """Delete a checkpoint."""
        conn, task_store, cp_store = setup
        cp_id = cp_store.save_checkpoint(task_store, "temp")
        assert cp_store.delete_checkpoint(cp_id)
        assert len(cp_store.list_checkpoints()) == 0

    def test_restore_rehydrates_tasks(self, setup) -> None:
        """Restore checkpoint rehydrates task state."""
        conn, task_store, cp_store = setup
        tid = task_store.create_task("Original Task")
        task_store.update_task(tid, status="in_progress")
        cp_id = cp_store.save_checkpoint(task_store, "snapshot")

        # Modify tasks after checkpoint
        task_store.update_task(tid, status="completed")
        task_store.create_task("New Task After CP")
        assert len(task_store.list_tasks()) == 2

        # Create a simple session store wrapper that supports add_message with autocommit
        class _FakeSessionStore:
            def __init__(self, c):
                self._conn = c

            def add_message(self, session_id, role, content, *, autocommit=True):
                from datetime import UTC, datetime
                now = datetime.now(UTC).isoformat()
                self._conn.execute(
                    "INSERT INTO messages (session_id, role, content, token_count, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (session_id, role, content, 0, now),
                )
                if autocommit:
                    self._conn.commit()

        fake_ss = _FakeSessionStore(conn)
        result = cp_store.restore_checkpoint(cp_id, task_store, fake_ss)
        assert result["label"] == "snapshot"

        # Tasks should be restored to checkpoint state
        tasks = task_store.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].title == "Original Task"
        assert tasks[0].status == "in_progress"

    def test_restore_rollback_on_failure(self, setup) -> None:
        """Restore rollback on mid-failure leaves no partial state."""
        conn, task_store, cp_store = setup
        task_store.create_task("Task Before")
        cp_id = cp_store.save_checkpoint(task_store, "safe point")

        # Add more tasks after checkpoint
        task_store.create_task("Task After")
        assert len(task_store.list_tasks()) == 2

        # Mock a session store that raises during add_message
        class _FailingSessionStore:
            def add_message(self, *args, **kwargs):
                raise RuntimeError("simulated failure")

        with pytest.raises(RuntimeError, match="simulated failure"):
            cp_store.restore_checkpoint(cp_id, task_store, _FailingSessionStore())

        # Original state should be preserved (transaction rolled back)
        tasks = task_store.list_tasks()
        assert len(tasks) == 2  # Still has both tasks

    def test_rejects_wrong_session(self, setup) -> None:
        """Restore rejects checkpoint from a different session."""
        conn, task_store, cp_store = setup
        cp_id = cp_store.save_checkpoint(task_store, "right session")

        # Create checkpoint store for different session
        other_store = CheckpointStore(conn, "other-sess")
        with pytest.raises(ValueError, match="not found"):
            other_store.restore_checkpoint(cp_id, task_store, None)

    def test_injects_context_summary(self, setup) -> None:
        """Restore injects context summary as system message."""
        conn, task_store, cp_store = setup
        cp_id = cp_store.save_checkpoint(
            task_store, "checkpoint-with-context",
            context_summary="We were working on feature X",
        )

        class _RecordingSessionStore:
            def __init__(self):
                self.messages = []

            def add_message(self, session_id, role, content, *, autocommit=True):
                self.messages.append((session_id, role, content))
                from datetime import UTC, datetime
                now = datetime.now(UTC).isoformat()
                conn.execute(
                    "INSERT INTO messages (session_id, role, content, token_count, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (session_id, role, content, 0, now),
                )
                if autocommit:
                    conn.commit()

        recorder = _RecordingSessionStore()
        cp_store.restore_checkpoint(cp_id, task_store, recorder)
        assert len(recorder.messages) == 1
        assert "We were working on feature X" in recorder.messages[0][2]
