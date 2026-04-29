"""Tests for CheckpointStore (Sprint 4C)."""

from __future__ import annotations

import json
import sqlite3

import pytest

from autocode.session.checkpoint_store import CheckpointStore
from autocode.session.models import ensure_tables
from autocode.session.store import SessionStore
from autocode.session.task_store import TaskStore


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

    def test_get_checkpoint_by_prefix(self, setup) -> None:
        """get_checkpoint accepts a unique ID prefix."""
        conn, task_store, cp_store = setup
        cp_id = cp_store.save_checkpoint(task_store, "prefixed")
        # Full ID works
        assert cp_store.get_checkpoint(cp_id) is not None
        # First 8 chars should be a unique prefix
        short = cp_id[:8]
        result = cp_store.get_checkpoint(short)
        assert result is not None
        assert result.id == cp_id
        assert result.label == "prefixed"

    def test_restore_rehydrates_messages_and_tool_calls(self, tmp_path) -> None:
        """Restoring a checkpoint restores conversation history and tool calls."""
        session_store = SessionStore(tmp_path / "sessions.db")
        session_id = session_store.create_session(
            title="Checkpoint chat",
            model="test-model",
            provider="test-provider",
            project_dir=".",
        )
        conn = session_store.get_connection()
        task_store = TaskStore(conn, session_id)
        cp_store = CheckpointStore(conn, session_id)

        session_store.add_message(session_id, "user", "Inspect src/app.py")
        assistant_id = session_store.add_message(
            session_id, "assistant", "I will inspect it"
        )
        tool_call_row_id = session_store.add_tool_call(
            session_id,
            assistant_id,
            "call-read",
            "read_file",
            {"path": "src/app.py"},
            status="completed",
        )
        session_store.update_tool_call(
            tool_call_row_id,
            "file contents",
            status="completed",
            duration_ms=12,
        )
        session_store.add_message(session_id, "tool", "file contents")

        cp_id = cp_store.save_checkpoint(
            task_store,
            "before edit",
            context_summary="Read src/app.py before editing.",
            session_store=session_store,
        )

        session_store.add_message(session_id, "user", "post-checkpoint message")
        cp_store.restore_checkpoint(cp_id, task_store, session_store)

        contents = [msg.content for msg in session_store.get_messages(session_id)]
        assert "Inspect src/app.py" in contents
        assert "I will inspect it" in contents
        assert "file contents" in contents
        assert "post-checkpoint message" not in contents
        assert any("[Restored checkpoint: before edit]" in msg for msg in contents)

        restored = session_store.get_messages_with_tool_calls(session_id)
        assistant_messages = [
            msg for msg in restored
            if msg["role"] == "assistant" and msg["content"] == "I will inspect it"
        ]
        assert assistant_messages
        assert assistant_messages[0]["tool_calls"] == [{
            "id": "call-read",
            "type": "function",
            "function": {
                "name": "read_file",
                "arguments": {"path": "src/app.py"},
            },
        }]

        row = conn.execute(
            "SELECT tool_name, result, status, duration_ms "
            "FROM tool_calls WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        assert dict(row) == {
            "tool_name": "read_file",
            "result": "file contents",
            "status": "completed",
            "duration_ms": 12,
        }

    def test_save_checkpoint_stores_bounded_message_snapshot(self, tmp_path) -> None:
        """Checkpoint message snapshots keep a summary and bounded recent messages."""
        session_store = SessionStore(tmp_path / "sessions.db")
        session_id = session_store.create_session(
            title="Checkpoint chat",
            model="test-model",
            provider="test-provider",
            project_dir=".",
        )
        task_store = TaskStore(session_store.get_connection(), session_id)
        cp_store = CheckpointStore(session_store.get_connection(), session_id)

        for index in range(7):
            session_store.add_message(session_id, "user", f"message {index}")

        cp_id = cp_store.save_checkpoint(
            task_store,
            "compact",
            context_summary="Earlier discussion summarized here.",
            session_store=session_store,
            message_limit=3,
        )

        checkpoint = cp_store.get_checkpoint(cp_id)
        assert checkpoint is not None
        snapshot = json.loads(checkpoint.messages_snapshot)
        assert snapshot["summary"] == "Earlier discussion summarized here."
        assert [msg["content"] for msg in snapshot["messages"]] == [
            "message 4",
            "message 5",
            "message 6",
        ]


class TestPerToolCheckpoint:
    """C4.G1: per-tool-call atomic checkpoint with diff-rollback."""

    def test_save_per_tool_checkpoint(self, setup) -> None:
        """save_per_tool_checkpoint stores kind=pre_tool with parent_tool_call_id."""
        conn, task_store, cp_store = setup
        task_store.create_task("Task A")
        cp_id = cp_store.save_per_tool_checkpoint(
            task_store,
            tool_call_id="tc-001",
            tool_name="write_file",
            tool_call_idx=0,
            kind="pre_tool",
            files_touched=["src/app.py", "lib/util.py"],
            label="pre write_file",
        )
        assert cp_id
        checkpoints = cp_store.list_checkpoints()
        assert len(checkpoints) == 1
        cp = checkpoints[0]
        assert cp.kind == "pre_tool"
        assert cp.parent_tool_call_id == "tc-001"
        assert cp.tool_call_idx == 0

    def test_list_per_tool_checkpoints_filters_by_kind(self, setup) -> None:
        """list_per_tool_checkpoints returns only per-tool checkpoints."""
        conn, task_store, cp_store = setup
        task_store.create_task("Task A")
        cp_store.save_checkpoint(task_store, "session checkpoint")
        cp_store.save_per_tool_checkpoint(
            task_store, "tc-001", "write_file", 0, "pre_tool",
            files_touched=["src/a.py"], label="pre write_file",
        )
        cp_store.save_per_tool_checkpoint(
            task_store, "tc-002", "edit_file", 1, "pre_tool",
            files_touched=["src/b.py"], label="pre edit_file",
        )
        per_tool = cp_store.list_per_tool_checkpoints()
        assert len(per_tool) == 2
        assert all(cp.kind in ("pre_tool", "post_tool") for cp in per_tool)

    def test_retention_drops_oldest_beyond_limit(self, setup) -> None:
        """Retention drops oldest per-tool checkpoints beyond N."""
        conn, task_store, cp_store = setup
        task_store.create_task("Task A")
        for i in range(5):
            cp_store.save_per_tool_checkpoint(
                task_store, f"tc-{i:03d}", "write_file", i, "pre_tool",
                files_touched=[f"src/file{i}.py"], label=f"pre write_file {i}",
            )
        per_tool = cp_store.list_per_tool_checkpoints()
        assert len(per_tool) == 5
        removed = cp_store.enforce_retention(limit=3)
        assert removed == 2
        remaining = cp_store.list_per_tool_checkpoints()
        assert len(remaining) == 3
        ids = [cp.parent_tool_call_id for cp in remaining]
        assert "tc-000" not in ids
        assert "tc-001" not in ids

    def test_restore_per_tool_checkpoint(self, setup) -> None:
        """Restoring a per-tool checkpoint rehydrates task state."""
        conn, task_store, cp_store = setup
        tid = task_store.create_task("Task A")
        task_store.update_task(tid, status="in_progress")
        cp_id = cp_store.save_per_tool_checkpoint(
            task_store, "tc-001", "write_file", 0, "pre_tool",
            files_touched=["src/app.py"], label="pre write_file",
        )
        task_store.update_task(tid, status="completed")
        task_store.create_task("Task B")

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
        assert result["label"] == "pre write_file"
        tasks = task_store.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].status == "in_progress"

    def test_old_session_checkpoints_load_after_migration(self, setup) -> None:
        """Old session-level checkpoints (no kind column) still load correctly."""
        conn, task_store, cp_store = setup
        task_store.create_task("Task A")
        cp_id = cp_store.save_checkpoint(task_store, "legacy checkpoint")
        cp = cp_store.get_checkpoint(cp_id)
        assert cp is not None
        assert cp.label == "legacy checkpoint"
        assert cp.kind is None or cp.kind == "session"

    def test_get_checkpoint_returns_files_touched(self, setup) -> None:
        """Per-tool checkpoint stores files_touched."""
        conn, task_store, cp_store = setup
        task_store.create_task("Task A")
        cp_id = cp_store.save_per_tool_checkpoint(
            task_store, "tc-001", "write_file", 0, "pre_tool",
            files_touched=["src/main.py", "lib/helper.py"],
            label="pre write_file",
        )
        cp = cp_store.get_checkpoint(cp_id)
        assert cp is not None
        assert json.loads(cp.active_files) == ["src/main.py", "lib/helper.py"]


class TestFileSnapshot:
    """C4.G1: local file-copy snapshot mechanism."""

    def test_snapshot_files_copies_to_disk(self, tmp_path) -> None:
        """snapshot_files copies specified files to snapshot directory."""
        from autocode.session.file_snapshot import snapshot_files

        src_dir = tmp_path / "project"
        src_dir.mkdir()
        (src_dir / "a.py").write_text("print('hello')")
        (src_dir / "b.py").write_text("print('world')")

        snap_dir = tmp_path / "snaps" / "sess-1" / "tc-001"
        snap_dir.mkdir(parents=True)

        snapshot_files(
            src_dir, snap_dir, files=["a.py", "b.py"],
        )

        assert (snap_dir / "a.py").read_text() == "print('hello')"
        assert (snap_dir / "b.py").read_text() == "print('world')"

    def test_snapshot_files_skips_missing(self, tmp_path) -> None:
        """snapshot_files silently skips files that don't exist."""
        from autocode.session.file_snapshot import snapshot_files

        src_dir = tmp_path / "project"
        src_dir.mkdir()
        (src_dir / "exists.py").write_text("content")

        snap_dir = tmp_path / "snaps" / "sess-1" / "tc-002"
        snap_dir.mkdir(parents=True)

        snapshot_files(
            src_dir, snap_dir, files=["exists.py", "missing.py"],
        )

        assert (snap_dir / "exists.py").read_text() == "content"
        assert not (snap_dir / "missing.py").exists()

    def test_restore_snapshot_overwrites_files(self, tmp_path) -> None:
        """restore_snapshot copies files back from snapshot to working tree."""
        from autocode.session.file_snapshot import snapshot_files, restore_snapshot

        src_dir = tmp_path / "project"
        src_dir.mkdir()
        (src_dir / "a.py").write_text("original")

        snap_dir = tmp_path / "snaps" / "sess-1" / "tc-003"
        snap_dir.mkdir(parents=True)

        snapshot_files(src_dir, snap_dir, files=["a.py"])
        (src_dir / "a.py").write_text("modified")

        restore_snapshot(snap_dir, src_dir)

        assert (src_dir / "a.py").read_text() == "original"

    def test_retention_cleans_oldest_snapshot_dirs(self, tmp_path) -> None:
        """Retention enforcement deletes oldest snapshot directories."""
        from autocode.session.file_snapshot import enforce_snapshot_retention

        base = tmp_path / "snaps" / "sess-1"
        for i in range(5):
            d = base / f"tc-{i:03d}"
            d.mkdir(parents=True)
            (d / "file.py").write_text(f"content {i}")

        removed = enforce_snapshot_retention(base, limit=3)
        assert removed == 2
        remaining = sorted(p.name for p in base.iterdir())
        assert remaining == ["tc-002", "tc-003", "tc-004"]
