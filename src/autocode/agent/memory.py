"""Episodic memory store: learned patterns that persist across sessions.

Memories are scoped to a project_id (not session_id) so they span sessions
within the same project. Categories: tool_pattern, user_preference,
project_fact, error_resolution.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

_VALID_CATEGORIES = {"tool_pattern", "user_preference", "project_fact", "error_resolution"}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class MemoryStore:
    """CRUD operations for learned memories in SQLite.

    Follows EpisodeStore pattern: takes a connection and project_id.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        project_id: str,
        *,
        max_entries: int = 200,
        max_context_tokens: int = 500,
        jaccard_threshold: float = 0.7,
    ) -> None:
        self._conn = conn
        self._project_id = project_id
        self._max_entries = max_entries
        self._max_context_tokens = max_context_tokens
        self._jaccard_threshold = jaccard_threshold

    def save(self, category: str, content: str, session_id: str) -> str:
        """Save a memory, deduplicating via Jaccard similarity.

        If a near-duplicate exists (Jaccard >= threshold), boosts the
        existing memory's relevance instead of creating a new one.
        Returns the memory ID (new or existing).
        """
        if category not in _VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category '{category}'. Valid: {', '.join(sorted(_VALID_CATEGORIES))}"
            )

        # Check for duplicates
        existing = self._get_project_memories()
        for mem in existing:
            sim = self._jaccard_similarity(content, mem["content"])
            if sim >= self._jaccard_threshold:
                # Boost existing memory relevance
                new_relevance = min(1.0, mem["relevance"] + 0.1)
                self._conn.execute(
                    "UPDATE memories SET relevance = ?, updated_at = ? WHERE id = ?",
                    (new_relevance, _now_iso(), mem["id"]),
                )
                self._conn.commit()
                logger.debug(
                    "Dedup: boosted memory %s (sim=%.2f)", mem["id"], sim,
                )
                return mem["id"]

        # Enforce retention
        self._enforce_retention()

        memory_id = uuid.uuid4().hex[:12]
        now = _now_iso()
        self._conn.execute(
            "INSERT INTO memories "
            "(id, session_id, project_id, category, content, relevance, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (memory_id, session_id, self._project_id, category, content, 1.0, now, now),
        )
        self._conn.commit()
        return memory_id

    def get_memories(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get memories for this project ordered by relevance DESC."""
        cursor = self._conn.execute(
            "SELECT * FROM memories WHERE project_id = ? "
            "ORDER BY relevance DESC LIMIT ?",
            (self._project_id, limit),
        )
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def get_context(self) -> str:
        """Get formatted memory context for prompt injection within token budget."""
        memories = self.get_memories()
        if not memories:
            return ""

        lines: list[str] = []
        chars_used = 0
        # ~4 chars per token
        max_chars = self._max_context_tokens * 4

        for mem in memories:
            line = f"- [{mem['category']}] {mem['content']}"
            if chars_used + len(line) > max_chars:
                break
            lines.append(line)
            chars_used += len(line) + 1  # +1 for newline

        return "\n".join(lines)

    def apply_decay(self) -> int:
        """Apply decay (relevance *= 0.95), delete below 0.1.

        Call at session start. Returns count of deleted memories.
        """
        self._conn.execute(
            "UPDATE memories SET relevance = relevance * 0.95 WHERE project_id = ?",
            (self._project_id,),
        )
        cursor = self._conn.execute(
            "DELETE FROM memories WHERE project_id = ? AND relevance < 0.1",
            (self._project_id,),
        )
        self._conn.commit()
        deleted = cursor.rowcount
        if deleted:
            logger.info("Memory decay: deleted %d stale memories", deleted)
        return deleted

    def delete(self, memory_id: str) -> bool:
        """Delete a specific memory. Returns True if deleted."""
        cursor = self._conn.execute(
            "DELETE FROM memories WHERE id = ? AND project_id = ?",
            (memory_id, self._project_id),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    async def learn_from_session(
        self,
        session_id: str,
        session_store: Any,
        provider: Any,
        scheduler: Any | None = None,
    ) -> list[str]:
        """Use LLM to extract up to 5 memories from a session.

        If scheduler is provided, uses background priority. Otherwise
        calls provider directly as fallback.

        Returns list of saved memory IDs.
        """
        messages = session_store.get_messages(session_id)
        if not messages:
            return []

        # Build a compact transcript
        transcript_lines = []
        for msg in messages[-20:]:  # Last 20 messages
            transcript_lines.append(f"{msg.role}: {msg.content[:200]}")
        transcript = "\n".join(transcript_lines)

        prompt = (
            "Extract up to 5 reusable memories from this coding session transcript. "
            "Each memory should be a pattern, preference, fact, or error resolution "
            "that would help in future sessions.\n\n"
            "Return JSON array of objects with 'category' (one of: tool_pattern, "
            "user_preference, project_fact, error_resolution) and 'content' (string).\n\n"
            f"Transcript:\n{transcript}\n\nJSON:"
        )

        llm_messages = [
            {"role": "system", "content": "Extract reusable memories as JSON."},
            {"role": "user", "content": prompt},
        ]

        try:
            if scheduler:
                response = await scheduler.submit(
                    provider.generate_with_tools(llm_messages, []),
                    foreground=False,
                )
            else:
                response = await provider.generate_with_tools(llm_messages, [])

            # Parse JSON from response
            text = response.content or ""
            # Try to extract JSON array
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                items = json.loads(text[start:end])
            else:
                return []

            saved_ids: list[str] = []
            for item in items[:5]:
                category = item.get("category", "")
                content = item.get("content", "")
                if category in _VALID_CATEGORIES and content:
                    mid = self.save(category, content, session_id)
                    saved_ids.append(mid)

            return saved_ids

        except Exception:
            logger.exception("Failed to learn from session %s", session_id)
            return []

    @staticmethod
    def _jaccard_similarity(a: str, b: str) -> float:
        """Word-set Jaccard similarity for dedup."""
        set_a = set(a.lower().split())
        set_b = set(b.lower().split())
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union)

    def _get_project_memories(self) -> list[dict[str, Any]]:
        """Get all memories for this project."""
        cursor = self._conn.execute(
            "SELECT id, content, relevance FROM memories WHERE project_id = ?",
            (self._project_id,),
        )
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def _enforce_retention(self) -> None:
        """Delete lowest-relevance memories beyond max_entries."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM memories WHERE project_id = ?",
            (self._project_id,),
        ).fetchone()
        count = row[0]
        if count < self._max_entries:
            return
        excess = count - self._max_entries + 1
        self._conn.execute(
            "DELETE FROM memories WHERE id IN ("
            "  SELECT id FROM memories WHERE project_id = ? "
            "  ORDER BY relevance ASC LIMIT ?"
            ")",
            (self._project_id, excess),
        )
        self._conn.commit()
