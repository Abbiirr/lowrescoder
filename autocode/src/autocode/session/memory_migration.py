"""Migration helpers for legacy SQLite memories."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from autocode.session.memory_fs import MemoryFS

CATEGORY_TOPIC = {
    "tool_pattern": "patterns",
    "user_preference": "preferences",
    "project_fact": "facts",
    "error_resolution": "debugging",
}


@dataclass(frozen=True)
class MigrationResult:
    migrated_count: int
    archive_table: str
    topics: dict[str, int]


def migrate_sqlite_memories(
    db_path: str | Path,
    memory_fs: MemoryFS,
    *,
    archive_date: str | None = None,
) -> MigrationResult:
    db_path = Path(db_path).expanduser()
    archive_date = archive_date or datetime.now(UTC).strftime("%Y%m%d")
    archive_table = f"memories_archive_{archive_date}"
    conn = sqlite3.connect(db_path)
    try:
        existing = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "memories" not in existing:
            return MigrationResult(0, archive_table, {})

        rows = list(
            conn.execute(
                "SELECT category, content FROM memories ORDER BY category, created_at, id"
            )
        )
        grouped: dict[str, list[str]] = {}
        for category, content in rows:
            topic = CATEGORY_TOPIC.get(str(category), "miscellany")
            grouped.setdefault(topic, []).append(f"- [{category}] {content}")

        for topic, entries in grouped.items():
            memory_fs.write_topic(
                topic,
                "\n".join(entries) + "\n",
                summary=f"Migrated {len(entries)} entries from SQLite memory",
            )

        conn.execute(f"ALTER TABLE memories RENAME TO {archive_table}")  # noqa: S608
        conn.commit()
        return MigrationResult(
            len(rows),
            archive_table,
            {topic: len(entries) for topic, entries in grouped.items()},
        )
    finally:
        conn.close()
