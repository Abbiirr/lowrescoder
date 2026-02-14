"""Tests for TaskStore — CRUD, DAG, cycle detection (Sprint 4A)."""

from __future__ import annotations

import pytest

from hybridcoder.session.store import SessionStore
from hybridcoder.session.task_store import TaskStore


@pytest.fixture
def session_store(tmp_path):
    """Create a SessionStore backed by a temp DB."""
    db_path = tmp_path / "test.db"
    store = SessionStore(str(db_path))
    yield store
    store.close()


@pytest.fixture
def task_store(session_store):
    """Create a TaskStore with a fresh session."""
    session_id = session_store.create_session(
        title="test", model="test", provider="test",
    )
    return TaskStore(session_store.get_connection(), session_id)


class TestTaskStoreCRUD:
    def test_create_task(self, task_store):
        task_id = task_store.create_task("Test task", description="A test")
        assert len(task_id) == 8
        task = task_store.get_task(task_id)
        assert task is not None
        assert task.title == "Test task"
        assert task.description == "A test"
        assert task.status == "pending"

    def test_get_task(self, task_store):
        task_id = task_store.create_task("Fetch me")
        task = task_store.get_task(task_id)
        assert task is not None
        assert task.id == task_id
        assert task.title == "Fetch me"

    def test_update_task_status(self, task_store):
        task_id = task_store.create_task("Update me")
        task_store.update_task(task_id, status="in_progress")
        task = task_store.get_task(task_id)
        assert task.status == "in_progress"
        task_store.update_task(task_id, status="completed")
        task = task_store.get_task(task_id)
        assert task.status == "completed"

    def test_list_tasks(self, task_store):
        task_store.create_task("Task A")
        task_store.create_task("Task B")
        task_store.create_task("Task C")
        tasks = task_store.list_tasks()
        assert len(tasks) == 3
        titles = [t.title for t in tasks]
        assert "Task A" in titles
        assert "Task B" in titles
        assert "Task C" in titles


class TestTaskStoreDependencies:
    def test_add_dependency(self, task_store):
        a = task_store.create_task("A")
        b = task_store.create_task("B")
        task_store.add_dependency(b, a)  # B depends on A
        deps = task_store.get_dependencies(b)
        assert a in deps

    def test_cycle_detection_rejects(self, task_store):
        a = task_store.create_task("A")
        b = task_store.create_task("B")
        c = task_store.create_task("C")
        task_store.add_dependency(b, a)  # B -> A
        task_store.add_dependency(c, b)  # C -> B
        with pytest.raises(ValueError, match="Cycle detected"):
            task_store.add_dependency(a, c)  # A -> C would create cycle

    def test_self_dependency_rejected(self, task_store):
        a = task_store.create_task("A")
        with pytest.raises(ValueError, match="Cycle detected"):
            task_store.add_dependency(a, a)

    def test_is_ready(self, task_store):
        a = task_store.create_task("A")
        b = task_store.create_task("B")
        task_store.add_dependency(b, a)

        # B not ready — A is pending
        assert not task_store.is_ready(b)

        # Complete A — now B is ready
        task_store.update_task(a, status="completed")
        assert task_store.is_ready(b)

    def test_snapshot_restore(self, task_store):
        a = task_store.create_task("A")
        b = task_store.create_task("B")
        task_store.add_dependency(b, a)
        task_store.update_task(a, status="completed")

        snapshot = task_store.snapshot()
        assert len(snapshot["tasks"]) == 2
        assert len(snapshot["dependencies"]) == 1

        # Clear and restore
        task_store.restore_from_snapshot(snapshot)
        tasks = task_store.list_tasks()
        assert len(tasks) == 2
        deps = task_store.get_dependencies(b)
        assert a in deps
