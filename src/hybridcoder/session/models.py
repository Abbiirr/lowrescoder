"""Session data models and DDL for SQLite persistence."""

from __future__ import annotations

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
