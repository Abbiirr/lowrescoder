"""Tests for task tools — create, update, list (Sprint 4A)."""

from __future__ import annotations

import pytest

from hybridcoder.agent.task_tools import register_task_tools
from hybridcoder.agent.tools import ToolRegistry
from hybridcoder.session.store import SessionStore
from hybridcoder.session.task_store import TaskStore


@pytest.fixture
def session_store(tmp_path):
    db_path = tmp_path / "test.db"
    store = SessionStore(str(db_path))
    yield store
    store.close()


@pytest.fixture
def task_store(session_store):
    session_id = session_store.create_session(
        title="test", model="test", provider="test",
    )
    return TaskStore(session_store.get_connection(), session_id)


@pytest.fixture
def registry(task_store):
    reg = ToolRegistry()
    register_task_tools(reg, task_store)
    return reg


class TestTaskTools:
    def test_create_task_tool(self, registry, task_store):
        tool = registry.get("create_task")
        result = tool.handler(title="Write tests")
        assert "Write tests" in result
        assert "Current tasks:" in result
        tasks = task_store.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].title == "Write tests"

    def test_update_task_tool(self, registry, task_store):
        task_id = task_store.create_task("Fix bug")
        tool = registry.get("update_task")
        result = tool.handler(task_id=task_id, status="in_progress")
        assert "Updated" in result
        assert "Current tasks:" in result
        task = task_store.get_task(task_id)
        assert task.status == "in_progress"

    def test_add_task_dependency_tool(self, registry, task_store):
        first = task_store.create_task("Implement")
        second = task_store.create_task("Tests")
        tool = registry.get("add_task_dependency")
        result = tool.handler(task_id=second, depends_on=first)
        assert "Added dependency" in result
        assert "Current tasks:" in result
        deps = task_store.get_dependencies(second)
        assert first in deps

    def test_list_tasks_tool(self, registry, task_store):
        task_store.create_task("Task A")
        task_store.create_task("Task B")
        tool = registry.get("list_tasks")
        result = tool.handler()
        assert "Task A" in result
        assert "Task B" in result

    def test_create_task_missing_title(self, registry):
        tool = registry.get("create_task")
        result = tool.handler(title="")
        assert "Error" in result

    def test_update_nonexistent_task(self, registry):
        tool = registry.get("update_task")
        result = tool.handler(task_id="nonexist", status="completed")
        assert "Error" in result or "not found" in result

    def test_tools_registered(self, registry):
        names = [t.name for t in registry.get_all()]
        assert "create_task" in names
        assert "update_task" in names
        assert "list_tasks" in names
        assert "add_task_dependency" in names


class TestTaskToolLogging:
    """Test that task tools emit structured log events (BUG-19)."""

    def test_create_task_logs_event(self, registry, caplog):
        with caplog.at_level("INFO", logger="hybridcoder.agent.task_tools"):
            tool = registry.get("create_task")
            tool.handler(title="Log test")
        assert any("task_created" in r.message for r in caplog.records)

    def test_update_task_logs_event(self, registry, task_store, caplog):
        task_id = task_store.create_task("Log update")
        with caplog.at_level("INFO", logger="hybridcoder.agent.task_tools"):
            tool = registry.get("update_task")
            tool.handler(task_id=task_id, status="in_progress")
        assert any("task_updated" in r.message for r in caplog.records)

    def test_add_dependency_logs_event(self, registry, task_store, caplog):
        first = task_store.create_task("First")
        second = task_store.create_task("Second")
        with caplog.at_level("INFO", logger="hybridcoder.agent.task_tools"):
            tool = registry.get("add_task_dependency")
            tool.handler(task_id=second, depends_on=first)
        assert any("task_dependency_added" in r.message for r in caplog.records)
