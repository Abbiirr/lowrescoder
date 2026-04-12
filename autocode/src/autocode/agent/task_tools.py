"""Task management tools for the agent (create, update, list tasks)."""

from __future__ import annotations

import logging

from autocode.agent.tools import ToolDefinition, ToolRegistry
from autocode.core.logging import log_event
from autocode.session.task_store import TaskStore

logger = logging.getLogger(__name__)


def _make_create_handler(task_store: TaskStore):
    def handler(
        title: str = "",
        description: str = "",
        depends_on: list[str] | None = None,
        **_kwargs,
    ) -> str:
        if not title:
            return "Error: title is required to create a task."
        task_id = task_store.create_task(title=title, description=description)
        log_event(
            logger, logging.INFO, "task_created",
            task_id=task_id, title=title, session_id=task_store.session_id,
        )
        if depends_on:
            for dep_id in depends_on:
                try:
                    task_store.add_dependency(task_id, dep_id)
                except ValueError as e:
                    return f"Error adding dependency to '{task_id}': {e}"
        return (
            f"Created task '{title}' (id: {task_id})\n"
            "Current tasks:\n"
            f"{task_store.summary()}"
        )
    return handler


def _make_update_handler(task_store: TaskStore):
    def handler(task_id: str = "", **kwargs) -> str:
        if not task_id:
            return "Error: task_id is required."
        task = task_store.get_task(task_id)
        if task is None:
            return f"Error: task '{task_id}' not found."
        fields = {k: v for k, v in kwargs.items() if k in ("status", "title", "description") and v}
        if not fields:
            return "Error: no valid fields to update."
        task_store.update_task(task_id, **fields)
        log_event(
            logger, logging.INFO, "task_updated",
            task_id=task_id, fields=fields, session_id=task_store.session_id,
        )
        return (
            f"Updated task '{task_id}': {fields}\n"
            "Current tasks:\n"
            f"{task_store.summary()}"
        )
    return handler


def _make_list_handler(task_store: TaskStore):
    def handler(**_kwargs) -> str:
        return task_store.summary()
    return handler


def _make_add_dependency_handler(task_store: TaskStore):
    def handler(task_id: str = "", depends_on: str = "", **_kwargs) -> str:
        if not task_id or not depends_on:
            return "Error: task_id and depends_on are required."
        if task_store.get_task(task_id) is None:
            return f"Error: task '{task_id}' not found."
        if task_store.get_task(depends_on) is None:
            return f"Error: dependency task '{depends_on}' not found."
        try:
            task_store.add_dependency(task_id, depends_on)
        except ValueError as e:
            return f"Error: {e}"
        log_event(
            logger, logging.INFO, "task_dependency_added",
            task_id=task_id, depends_on=depends_on, session_id=task_store.session_id,
        )
        return (
            f"Added dependency: '{task_id}' depends on '{depends_on}'\n"
            "Current tasks:\n"
            f"{task_store.summary()}"
        )
    return handler


def register_task_tools(registry: ToolRegistry, task_store: TaskStore) -> None:
    """Register create_task, update_task, and list_tasks tools into the registry."""
    registry.register(ToolDefinition(
        name="create_task",
        description="Create a new task to track work. Returns the task ID.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short title for the task"},
                "description": {"type": "string", "description": "Detailed description (optional)"},
                "depends_on": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of task IDs that must complete first",
                },
            },
            "required": ["title"],
        },
        handler=_make_create_handler(task_store),
    ))

    registry.register(ToolDefinition(
        name="update_task",
        description="Update a task's status, title, or description.",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "ID of the task to update"},
                "status": {
                    "type": "string",
                    "description": "New status (pending, in_progress, completed)",
                },
                "title": {"type": "string", "description": "New title (optional)"},
                "description": {"type": "string", "description": "New description (optional)"},
            },
            "required": ["task_id"],
        },
        handler=_make_update_handler(task_store),
    ))

    registry.register(ToolDefinition(
        name="list_tasks",
        description="List all tasks with their status and any blockers.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=_make_list_handler(task_store),
    ))

    registry.register(ToolDefinition(
        name="add_task_dependency",
        description="Add a dependency: task_id depends on depends_on task_id.",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task that is blocked"},
                "depends_on": {"type": "string", "description": "Task that must complete first"},
            },
            "required": ["task_id", "depends_on"],
        },
        handler=_make_add_dependency_handler(task_store),
    ))
