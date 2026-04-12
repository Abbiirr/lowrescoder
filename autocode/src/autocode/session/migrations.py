"""Schema migration subsystem — version-tracked DDL changes.

Each migration is a function that receives a sqlite3.Connection and applies
DDL changes. Migrations are registered in the MIGRATIONS list and applied
in order. The schema_version table tracks which migrations have been applied.

Usage:
    from autocode.session.migrations import run_migrations
    run_migrations(conn)  # applies all pending migrations
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Return the current schema version, or 0 if no migrations have run."""
    try:
        cursor = conn.execute(
            "SELECT MAX(version) FROM schema_version",
        )
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else 0
    except sqlite3.OperationalError:
        return 0


# ---------------------------------------------------------------------------
# Individual migration functions
# ---------------------------------------------------------------------------


def _migrate_v1(conn: sqlite3.Connection) -> None:
    """v1: orchestrator_events table for canonical event schema."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS orchestrator_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            trace_id TEXT NOT NULL DEFAULT '',
            span_id TEXT NOT NULL DEFAULT '',
            parent_span_id TEXT NOT NULL DEFAULT '',
            source_agent TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            task_id TEXT NOT NULL DEFAULT '',
            payload TEXT NOT NULL DEFAULT '{}',
            metadata TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_orch_events_session
            ON orchestrator_events(session_id);
        CREATE INDEX IF NOT EXISTS idx_orch_events_trace
            ON orchestrator_events(trace_id);
        CREATE INDEX IF NOT EXISTS idx_orch_events_type
            ON orchestrator_events(event_type);
        CREATE INDEX IF NOT EXISTS idx_orch_events_task
            ON orchestrator_events(task_id);
    """)


# ---------------------------------------------------------------------------
# Migration registry
# ---------------------------------------------------------------------------

def _migrate_v2(conn: sqlite3.Connection) -> None:
    """v2: agent_mailbox table for persistent messaging."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agent_mailbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL UNIQUE,
            session_id TEXT NOT NULL,
            from_agent TEXT NOT NULL,
            to_agent TEXT,
            message_type TEXT NOT NULL DEFAULT 'request',
            status TEXT NOT NULL DEFAULT 'pending',
            payload TEXT NOT NULL DEFAULT '{}',
            task_id TEXT,
            claimed_by TEXT,
            claim_until TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_mailbox_session
            ON agent_mailbox(session_id);
        CREATE INDEX IF NOT EXISTS idx_mailbox_to_agent
            ON agent_mailbox(to_agent);
        CREATE INDEX IF NOT EXISTS idx_mailbox_task
            ON agent_mailbox(task_id);
        CREATE INDEX IF NOT EXISTS idx_mailbox_status
            ON agent_mailbox(status);
    """)


def _migrate_v3(conn: sqlite3.Connection) -> None:
    """v3: task board columns + task_artifacts + task_status_history tables."""
    # New columns on tasks table (safe: ALTER TABLE ADD COLUMN is idempotent-ish)
    for col_sql in [
        "ALTER TABLE tasks ADD COLUMN owner_agent TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tasks ADD COLUMN claimed_at TEXT",
        "ALTER TABLE tasks ADD COLUMN lease_expires_at TEXT",
        "ALTER TABLE tasks ADD COLUMN priority INTEGER NOT NULL DEFAULT 0",
    ]:
        try:
            conn.execute(col_sql)
        except sqlite3.OperationalError:
            pass  # column already exists

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS task_artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            artifact_type TEXT NOT NULL,
            path TEXT NOT NULL DEFAULT '',
            content_hash TEXT NOT NULL DEFAULT '',
            metadata TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_task_artifacts_task
            ON task_artifacts(task_id);

        CREATE TABLE IF NOT EXISTS task_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            old_status TEXT NOT NULL,
            new_status TEXT NOT NULL,
            changed_by TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '',
            changed_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_task_history_task
            ON task_status_history(task_id);
    """)


MIGRATIONS: list[tuple[int, str, Callable[[sqlite3.Connection], None]]] = [
    (1, "orchestrator_events table", _migrate_v1),
    (2, "agent_mailbox table", _migrate_v2),
    (3, "task board columns and tables", _migrate_v3),
]
"""List of (version, description, function) in ascending order."""


def run_migrations(conn: sqlite3.Connection) -> int:
    """Apply all pending migrations and return the final schema version.

    Safe to call multiple times — already-applied migrations are skipped.
    """
    current = get_schema_version(conn)

    for version, description, func in MIGRATIONS:
        if version <= current:
            continue
        logger.info("Applying migration v%d: %s", version, description)
        func(conn)
        conn.execute(
            "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
            (version, datetime.now(UTC).isoformat()),
        )
        conn.commit()
        logger.info("Migration v%d applied successfully", version)

    return get_schema_version(conn)
