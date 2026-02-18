"""Session data models and DDL for SQLite persistence."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from pydantic import BaseModel

DDL = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    model TEXT NOT NULL,
    provider TEXT NOT NULL,
    project_dir TEXT NOT NULL DEFAULT '',
    summary TEXT,
    token_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);

CREATE TABLE IF NOT EXISTS tool_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    message_id INTEGER NOT NULL REFERENCES messages(id),
    tool_call_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    arguments TEXT NOT NULL DEFAULT '{}',
    result TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    duration_ms INTEGER,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_calls_message ON tool_calls(message_id);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_session ON tasks(session_id);

CREATE TABLE IF NOT EXISTS task_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    task_id TEXT NOT NULL REFERENCES tasks(id),
    depends_on TEXT NOT NULL REFERENCES tasks(id),
    UNIQUE(task_id, depends_on),
    CHECK(task_id != depends_on)
);
CREATE INDEX IF NOT EXISTS idx_task_deps_task ON task_dependencies(task_id);

CREATE TABLE IF NOT EXISTS episodes (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    sequence_num INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    outcome TEXT,
    metrics TEXT DEFAULT '{}',
    UNIQUE(session_id, sequence_num)
);
CREATE INDEX IF NOT EXISTS idx_episodes_session ON episodes(session_id);

CREATE TABLE IF NOT EXISTS episode_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id TEXT NOT NULL REFERENCES episodes(id),
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    data TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_events_episode ON episode_events(episode_id);
-- Sprint 4C: memories + checkpoints
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    project_id TEXT NOT NULL,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    relevance REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memories_session ON memories(session_id);
CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project_id);

CREATE TABLE IF NOT EXISTS checkpoints (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    label TEXT NOT NULL,
    tasks_snapshot TEXT NOT NULL DEFAULT '{}',
    context_summary TEXT NOT NULL DEFAULT '',
    active_files TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_checkpoints_session ON checkpoints(session_id);
"""


class SessionRow(BaseModel):
    """A session record."""

    id: str
    title: str
    model: str
    provider: str
    project_dir: str = ""
    summary: str | None = None
    token_count: int = 0
    created_at: datetime
    updated_at: datetime


class MessageRow(BaseModel):
    """A message record within a session."""

    id: int
    session_id: str
    role: str
    content: str
    token_count: int = 0
    created_at: datetime


class ToolCallRow(BaseModel):
    """A tool call record linked to a message."""

    id: int
    session_id: str
    message_id: int
    tool_call_id: str
    tool_name: str
    arguments: str = "{}"
    result: str | None = None
    status: str = "pending"
    duration_ms: int | None = None
    created_at: datetime


class TaskRow(BaseModel):
    """A task record within a session."""

    id: str
    session_id: str
    title: str
    description: str = ""
    status: str = "pending"
    created_at: datetime
    updated_at: datetime


class MemoryRow(BaseModel):
    """A learned memory record scoped to a project."""

    id: str
    session_id: str
    project_id: str
    category: str
    content: str
    relevance: float = 1.0
    created_at: datetime
    updated_at: datetime


class CheckpointRow(BaseModel):
    """A checkpoint snapshot of task state."""

    id: str
    session_id: str
    label: str
    tasks_snapshot: str = "{}"
    context_summary: str = ""
    active_files: str = "[]"
    created_at: datetime


def ensure_tables(conn: sqlite3.Connection) -> None:
    """Run the full DDL idempotently (safe to call multiple times)."""
    conn.executescript(DDL)
