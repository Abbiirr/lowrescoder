"""SQLite-backed store for crystallized per-session user intent."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list | tuple):
        return [str(item) for item in value if str(item)]
    return [str(value)]


def _read_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return _string_list(parsed)


@dataclass(slots=True)
class Intent:
    """Crystallized original user intent for Ralph-style recovery."""

    session_id: str
    original_goal: str
    captured_at: str
    success_criteria: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    progress_so_far: list[str] = field(default_factory=list)


IntentExtractor = Callable[[str], Mapping[str, Any]]


class IntentStore:
    """Persist and update one intent record per session."""

    def __init__(self, db_path: str | Path) -> None:
        path = Path(db_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = path
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS session_intents (
                session_id TEXT PRIMARY KEY,
                original_goal TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                success_criteria_json TEXT NOT NULL DEFAULT '[]',
                constraints_json TEXT NOT NULL DEFAULT '[]',
                progress_so_far_json TEXT NOT NULL DEFAULT '[]',
                updated_at TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def capture(
        self,
        session_id: str,
        user_message: str,
        *,
        extractor: IntentExtractor | None = None,
    ) -> Intent:
        """Capture initial session intent, replacing any prior row for the session."""

        extracted = dict(extractor(user_message) if extractor else {})
        now = _now_iso()
        intent = Intent(
            session_id=session_id,
            original_goal=str(extracted.get("original_goal") or user_message),
            captured_at=now,
            success_criteria=_string_list(extracted.get("success_criteria")),
            constraints=_string_list(extracted.get("constraints")),
            progress_so_far=_string_list(extracted.get("progress_so_far")),
        )
        self._upsert(intent, updated_at=now)
        return intent

    def get(self, session_id: str) -> Intent | None:
        """Return the persisted intent for a session, if any."""

        row = self._conn.execute(
            "SELECT * FROM session_intents WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        return Intent(
            session_id=str(row["session_id"]),
            original_goal=str(row["original_goal"]),
            captured_at=str(row["captured_at"]),
            success_criteria=_read_json_list(row["success_criteria_json"]),
            constraints=_read_json_list(row["constraints_json"]),
            progress_so_far=_read_json_list(row["progress_so_far_json"]),
        )

    def update(self, intent: Intent) -> Intent:
        """Update intent metadata while appending progress instead of replacing it."""

        existing = self.get(intent.session_id)
        if existing is not None:
            intent.progress_so_far = _append_unique(
                existing.progress_so_far,
                intent.progress_so_far,
            )
            if not intent.captured_at:
                intent.captured_at = existing.captured_at
        self._upsert(intent, updated_at=_now_iso())
        return intent

    def append_progress(self, session_id: str, progress: str) -> Intent | None:
        """Append one progress item to an existing intent."""

        intent = self.get(session_id)
        if intent is None:
            return None
        intent.progress_so_far = _append_unique(intent.progress_so_far, [progress])
        self._upsert(intent, updated_at=_now_iso())
        return intent

    def _upsert(self, intent: Intent, *, updated_at: str) -> None:
        self._conn.execute(
            """
            INSERT INTO session_intents (
                session_id,
                original_goal,
                captured_at,
                success_criteria_json,
                constraints_json,
                progress_so_far_json,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                original_goal = excluded.original_goal,
                captured_at = excluded.captured_at,
                success_criteria_json = excluded.success_criteria_json,
                constraints_json = excluded.constraints_json,
                progress_so_far_json = excluded.progress_so_far_json,
                updated_at = excluded.updated_at
            """,
            (
                intent.session_id,
                intent.original_goal,
                intent.captured_at,
                json.dumps(intent.success_criteria),
                json.dumps(intent.constraints),
                json.dumps(intent.progress_so_far),
                updated_at,
            ),
        )
        self._conn.commit()


def _append_unique(existing: list[str], additions: list[str]) -> list[str]:
    result = list(existing)
    for item in additions:
        if item and item not in result:
            result.append(item)
    return result
