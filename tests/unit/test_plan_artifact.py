"""Tests for PlanArtifact (Sprint 4C)."""

from __future__ import annotations

import sqlite3

import pytest

from hybridcoder.agent.plan_artifact import export, sync_from_markdown
from hybridcoder.session.models import ensure_tables
from hybridcoder.session.task_store import TaskStore


@pytest.fixture()
def task_store():
    """In-memory SQLite + TaskStore fixture."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_tables(conn)
    conn.execute(
        "INSERT INTO sessions (id, title, model, provider, project_dir, created_at, updated_at) "
        "VALUES ('sess-1', 'Test', 'test', 'test', '.', '2024-01-01', '2024-01-01')"
    )
    conn.commit()
    return TaskStore(conn, "sess-1")


class TestPlanArtifact:
    """4 tests for PlanArtifact."""

    def test_export_creates_markdown(self, task_store: TaskStore, tmp_path) -> None:
        """export() creates a markdown file."""
        task_store.create_task("Implement feature")
        path = export("sess-1", task_store, project_root=tmp_path)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "# Plan: sess-1" in content

    def test_export_includes_checkboxes(self, task_store: TaskStore, tmp_path) -> None:
        """export() includes task checkboxes in markdown."""
        tid1 = task_store.create_task("Task A")
        tid2 = task_store.create_task("Task B")
        task_store.update_task(tid1, status="completed")
        path = export("sess-1", task_store, project_root=tmp_path)
        content = path.read_text(encoding="utf-8")
        assert f"[x] #{tid1}:" in content
        assert f"[ ] #{tid2}:" in content

    def test_sync_updates_status(self, task_store: TaskStore, tmp_path) -> None:
        """sync_from_markdown() updates task status from checkboxes."""
        tid1 = task_store.create_task("Task A")
        tid2 = task_store.create_task("Task B")

        # Create a plan file with tid1 completed and tid2 in progress
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(
            f"# Plan\n"
            f"- [x] #{tid1}: Task A\n"
            f"- [>] #{tid2}: Task B\n",
            encoding="utf-8",
        )

        updated = sync_from_markdown("sess-1", task_store, plan_file)
        assert tid1 in updated
        assert tid2 in updated

        t1 = task_store.get_task(tid1)
        t2 = task_store.get_task(tid2)
        assert t1.status == "completed"
        assert t2.status == "in_progress"

    def test_sync_ignores_unknown_ids(self, task_store: TaskStore, tmp_path) -> None:
        """sync_from_markdown() ignores IDs not in TaskStore."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(
            "# Plan\n"
            "- [x] #unknown123: Some task\n",
            encoding="utf-8",
        )
        updated = sync_from_markdown("sess-1", task_store, plan_file)
        assert updated == []
