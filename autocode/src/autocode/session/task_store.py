"""Task store with CRUD, DAG dependency management, cycle detection, and team board semantics."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from graphlib import CycleError, TopologicalSorter
from typing import Any

from autocode.session.models import TaskArtifactRow, TaskRow, TaskStatusHistoryRow


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

    def restore_from_snapshot(self, snapshot: dict, *, autocommit: bool = True) -> None:
        """Restore tasks and dependencies from a snapshot.

        When autocommit=False, the caller controls the transaction boundary
        (used by CheckpointStore for transactional restore).
        """
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

        if autocommit:
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

    # ── Team Board Semantics ──

    def _record_history(
        self, task_id: str, old_status: str, new_status: str,
        changed_by: str = "", reason: str = "",
    ) -> None:
        """Record a status transition in task_status_history."""
        self._conn.execute(
            "INSERT INTO task_status_history "
            "(task_id, session_id, old_status, new_status, changed_by, reason, changed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (task_id, self._session_id, old_status, new_status,
             changed_by, reason, _now_iso()),
        )

    def claim_task(
        self, task_id: str, agent_id: str, lease_seconds: int = 300,
    ) -> bool:
        """Claim a pending task. Returns True if claimed.

        Only pending tasks with all dependencies met can be claimed.
        """
        task = self.get_task(task_id)
        if task is None or task.status != "pending":
            return False
        if not self.is_ready(task_id):
            return False

        now = _now_iso()
        lease_until = (
            datetime.now(UTC) + timedelta(seconds=lease_seconds)
        ).isoformat()

        cursor = self._conn.execute(
            "UPDATE tasks SET status = 'in_progress', owner_agent = ?, "
            "claimed_at = ?, lease_expires_at = ?, updated_at = ? "
            "WHERE id = ? AND session_id = ? AND status = 'pending'",
            (agent_id, now, lease_until, now, task_id, self._session_id),
        )
        if cursor.rowcount == 0:
            return False  # concurrent claim won the race
        self._record_history(task_id, "pending", "in_progress", changed_by=agent_id)
        self._conn.commit()
        return True

    def release_task(self, task_id: str, agent_id: str) -> None:
        """Release a claimed task back to pending. Only the owner can release."""
        task = self.get_task(task_id)
        if task is None:
            return
        if task.owner_agent != agent_id:
            raise ValueError(
                f"Task {task_id} not owned by {agent_id}: "
                f"owned by '{task.owner_agent}'"
            )
        old_status = task.status
        now = _now_iso()
        self._conn.execute(
            "UPDATE tasks SET status = 'pending', owner_agent = '', "
            "claimed_at = NULL, lease_expires_at = NULL, updated_at = ? "
            "WHERE id = ? AND session_id = ?",
            (now, task_id, self._session_id),
        )
        self._record_history(task_id, old_status, "pending", changed_by=agent_id)
        self._conn.commit()

    def _transition_task(
        self, task_id: str, new_status: str, agent_id: str,
        reason: str = "", clear_owner: bool = False,
    ) -> None:
        """Transition a task to a new status with history recording."""
        task = self.get_task(task_id)
        if task is None:
            return
        old_status = task.status
        now = _now_iso()
        if clear_owner:
            self._conn.execute(
                "UPDATE tasks SET status = ?, owner_agent = '', "
                "claimed_at = NULL, lease_expires_at = NULL, updated_at = ? "
                "WHERE id = ? AND session_id = ?",
                (new_status, now, task_id, self._session_id),
            )
        else:
            self._conn.execute(
                "UPDATE tasks SET status = ?, updated_at = ? "
                "WHERE id = ? AND session_id = ?",
                (new_status, now, task_id, self._session_id),
            )
        self._record_history(task_id, old_status, new_status,
                             changed_by=agent_id, reason=reason)
        self._conn.commit()

    def complete_task(
        self, task_id: str, agent_id: str, reason: str = "",
    ) -> None:
        """Mark task completed by agent. Records history."""
        self._transition_task(task_id, "completed", agent_id, reason)

    def fail_task(
        self, task_id: str, agent_id: str, reason: str = "",
    ) -> None:
        """Mark task failed. Records history."""
        self._transition_task(task_id, "failed", agent_id, reason)

    def escalate_task(
        self, task_id: str, from_agent: str, reason: str = "",
    ) -> None:
        """Release task and mark for escalation."""
        self._transition_task(task_id, "escalated", from_agent, reason, clear_owner=True)

    def add_artifact(
        self, task_id: str, artifact_type: str, path: str = "",
        content_hash: str = "", metadata: dict[str, Any] | None = None,
    ) -> int:
        """Attach an artifact to a task. Returns artifact row ID."""
        now = _now_iso()
        cursor = self._conn.execute(
            "INSERT INTO task_artifacts "
            "(task_id, session_id, artifact_type, path, content_hash, metadata, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (task_id, self._session_id, artifact_type, path, content_hash,
             json.dumps(metadata or {}, default=str), now),
        )
        self._conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def get_artifacts(self, task_id: str) -> list[TaskArtifactRow]:
        """Get all artifacts for a task."""
        cursor = self._conn.execute(
            "SELECT * FROM task_artifacts WHERE task_id = ? AND session_id = ? "
            "ORDER BY created_at ASC",
            (task_id, self._session_id),
        )
        return [TaskArtifactRow(**dict(row)) for row in cursor.fetchall()]

    def get_status_history(self, task_id: str) -> list[TaskStatusHistoryRow]:
        """Get full status history for a task."""
        cursor = self._conn.execute(
            "SELECT * FROM task_status_history WHERE task_id = ? AND session_id = ? "
            "ORDER BY changed_at ASC",
            (task_id, self._session_id),
        )
        return [TaskStatusHistoryRow(**dict(row)) for row in cursor.fetchall()]

    def get_claimable_tasks(self) -> list[TaskRow]:
        """Get tasks that are pending and have all dependencies met."""
        tasks = self.list_tasks()
        return [
            t for t in tasks
            if t.status == "pending" and self.is_ready(t.id)
        ]

    def release_expired_claims(self) -> int:
        """Release tasks with expired leases back to pending. Returns count."""
        now = _now_iso()
        cursor = self._conn.execute(
            "UPDATE tasks SET status = 'pending', owner_agent = '', "
            "claimed_at = NULL, lease_expires_at = NULL, updated_at = ? "
            "WHERE status = 'in_progress' AND lease_expires_at < ? AND session_id = ?",
            (now, now, self._session_id),
        )
        self._conn.commit()
        return cursor.rowcount
