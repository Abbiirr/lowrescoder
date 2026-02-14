"""Task store with CRUD, DAG dependency management, and cycle detection."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from graphlib import CycleError, TopologicalSorter

from hybridcoder.session.models import TaskRow


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class TaskStore:
    """Manages tasks and their dependencies within a session.

    Tasks form a DAG (directed acyclic graph) via the task_dependencies table.
    Adding a dependency that would create a cycle raises ValueError.
    """

    def __init__(self, conn: sqlite3.Connection, session_id: str) -> None:
        self._conn = conn
        self._session_id = session_id

    @property
    def session_id(self) -> str:
        return self._session_id

    def create_task(
        self, title: str, description: str = "", status: str = "pending",
    ) -> str:
        """Create a new task and return its ID."""
        task_id = uuid.uuid4().hex[:8]
        now = _now_iso()
        self._conn.execute(
            "INSERT INTO tasks "
            "(id, session_id, title, description, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (task_id, self._session_id, title, description, status, now, now),
        )
        self._conn.commit()
        return task_id

    def get_task(self, task_id: str) -> TaskRow | None:
        """Retrieve a task by ID."""
        cursor = self._conn.execute(
            "SELECT * FROM tasks WHERE id = ? AND session_id = ?",
            (task_id, self._session_id),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return TaskRow(**dict(row))

    def update_task(self, task_id: str, **fields: str) -> None:
        """Update task fields (title, description, status)."""
        allowed = {"title", "description", "status"}
        filtered = {k: v for k, v in fields.items() if k in allowed}
        if not filtered:
            return
        filtered["updated_at"] = _now_iso()
        set_clause = ", ".join(f"{k} = ?" for k in filtered)
        values = list(filtered.values()) + [task_id, self._session_id]
        self._conn.execute(
            f"UPDATE tasks SET {set_clause} WHERE id = ? AND session_id = ?",  # noqa: S608
            values,
        )
        self._conn.commit()

    def list_tasks(self) -> list[TaskRow]:
        """List all tasks for this session."""
        cursor = self._conn.execute(
            "SELECT * FROM tasks WHERE session_id = ? ORDER BY created_at ASC",
            (self._session_id,),
        )
        return [TaskRow(**dict(row)) for row in cursor.fetchall()]

    def add_dependency(self, task_id: str, depends_on: str) -> None:
        """Add a dependency edge (task_id depends on depends_on).

        Raises ValueError if adding this edge would create a cycle.
        """
        if task_id == depends_on:
            raise ValueError(f"Cycle detected: {task_id} -> {depends_on}")

        # Build the full graph and validate with TopologicalSorter
        graph = self._build_graph()
        # Add proposed edge
        graph.setdefault(task_id, set()).add(depends_on)
        graph.setdefault(depends_on, set())

        sorter = TopologicalSorter(graph)
        try:
            sorter.prepare()
        except CycleError:
            raise ValueError(f"Cycle detected: {task_id} -> {depends_on}") from None

        # If valid, insert the dependency
        self._conn.execute(
            "INSERT INTO task_dependencies (session_id, task_id, depends_on) "
            "VALUES (?, ?, ?)",
            (self._session_id, task_id, depends_on),
        )
        self._conn.commit()

    def get_dependencies(self, task_id: str) -> list[str]:
        """Get IDs of tasks that this task depends on."""
        cursor = self._conn.execute(
            "SELECT depends_on FROM task_dependencies WHERE task_id = ? AND session_id = ?",
            (task_id, self._session_id),
        )
        return [row[0] for row in cursor.fetchall()]

    def get_dependents(self, task_id: str) -> list[str]:
        """Get IDs of tasks that depend on this task."""
        cursor = self._conn.execute(
            "SELECT task_id FROM task_dependencies WHERE depends_on = ? AND session_id = ?",
            (task_id, self._session_id),
        )
        return [row[0] for row in cursor.fetchall()]

    def is_ready(self, task_id: str) -> bool:
        """Return True if all dependencies of this task are completed."""
        deps = self.get_dependencies(task_id)
        if not deps:
            return True
        placeholders = ",".join("?" * len(deps))
        cursor = self._conn.execute(
            f"SELECT COUNT(*) FROM tasks WHERE id IN ({placeholders}) AND status != 'completed'",  # noqa: S608
            deps,
        )
        return cursor.fetchone()[0] == 0

    def get_blocked_reason(self, task_id: str) -> str | None:
        """Return a description of why the task is blocked, or None if ready."""
        deps = self.get_dependencies(task_id)
        if not deps:
            return None
        placeholders = ",".join("?" * len(deps))
        cursor = self._conn.execute(
            "SELECT id, title, status FROM tasks "  # noqa: S608
            f"WHERE id IN ({placeholders}) AND status != 'completed'",
            deps,
        )
        blockers = cursor.fetchall()
        if not blockers:
            return None
        names = [f"{row[1]} ({row[2]})" for row in blockers]
        return "blocked by: " + ", ".join(names)

    def summary(self) -> str:
        """Compact multiline summary of all tasks."""
        tasks = self.list_tasks()
        if not tasks:
            return "No tasks."
        lines = []
        for t in tasks:
            check = "x" if t.status == "completed" else " "
            suffix = ""
            reason = self.get_blocked_reason(t.id)
            if reason:
                suffix = f" ({reason})"
            elif t.status != "completed":
                suffix = f" ({t.status})"
            lines.append(f"[{check}] {t.title}{suffix}")
        return "\n".join(lines)

    def snapshot(self) -> dict:
        """Return a JSON-serializable snapshot of all tasks and dependencies."""
        tasks = self.list_tasks()
        deps = []
        for t in tasks:
            for dep_id in self.get_dependencies(t.id):
                deps.append({"task_id": t.id, "depends_on": dep_id})
        return {
            "tasks": [t.model_dump(mode="json") for t in tasks],
            "dependencies": deps,
        }

    def restore_from_snapshot(self, snapshot: dict) -> None:
        """Restore tasks and dependencies from a snapshot."""
        # Clear existing tasks for this session
        self._conn.execute(
            "DELETE FROM task_dependencies WHERE session_id = ?",
            (self._session_id,),
        )
        self._conn.execute(
            "DELETE FROM tasks WHERE session_id = ?",
            (self._session_id,),
        )

        # Restore tasks
        for t in snapshot.get("tasks", []):
            self._conn.execute(
                "INSERT INTO tasks "
                "(id, session_id, title, description, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (t["id"], self._session_id, t["title"], t.get("description", ""),
                 t.get("status", "pending"), t["created_at"], t["updated_at"]),
            )

        # Restore dependencies
        for dep in snapshot.get("dependencies", []):
            self._conn.execute(
                "INSERT INTO task_dependencies (session_id, task_id, depends_on) "
                "VALUES (?, ?, ?)",
                (self._session_id, dep["task_id"], dep["depends_on"]),
            )

        self._conn.commit()

    def _build_graph(self) -> dict[str, set[str]]:
        """Build the dependency graph from the database."""
        cursor = self._conn.execute(
            "SELECT task_id, depends_on FROM task_dependencies WHERE session_id = ?",
            (self._session_id,),
        )
        graph: dict[str, set[str]] = {}
        # Include all tasks as nodes
        for t in self.list_tasks():
            graph.setdefault(t.id, set())
        for row in cursor.fetchall():
            graph.setdefault(row[0], set()).add(row[1])
            graph.setdefault(row[1], set())
        return graph
