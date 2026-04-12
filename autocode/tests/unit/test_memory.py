"""Tests for MemoryStore (Sprint 4C)."""

from __future__ import annotations

import sqlite3

import pytest

from autocode.agent.memory import MemoryStore
from autocode.session.models import ensure_tables


@pytest.fixture()
def mem_store() -> MemoryStore:
    """In-memory SQLite + ensure_tables fixture."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_tables(conn)
    return MemoryStore(conn, "test-project", max_entries=10, max_context_tokens=100)


class TestMemoryStore:
    """7 tests for MemoryStore."""

    def test_save_and_retrieve(self, mem_store: MemoryStore) -> None:
        """Save a memory and retrieve it."""
        mid = mem_store.save("project_fact", "Uses pytest for testing", "sess-1")
        assert mid
        memories = mem_store.get_memories()
        assert len(memories) == 1
        assert memories[0]["content"] == "Uses pytest for testing"
        assert memories[0]["category"] == "project_fact"

    def test_dedup_jaccard_accept(self, mem_store: MemoryStore) -> None:
        """Near-duplicate memory boosts existing instead of creating new."""
        mid1 = mem_store.save("tool_pattern", "use read_file before write_file", "sess-1")
        # Almost identical (Jaccard should be >= 0.7)
        mid2 = mem_store.save("tool_pattern", "always use read_file before write_file", "sess-1")
        assert mid1 == mid2  # Same memory boosted (returns existing ID)
        memories = mem_store.get_memories()
        assert len(memories) == 1  # Only one entry, not two

    def test_dedup_jaccard_reject(self, mem_store: MemoryStore) -> None:
        """Dissimilar memories create separate entries."""
        mid1 = mem_store.save("project_fact", "Backend is Python", "sess-1")
        mid2 = mem_store.save("project_fact", "Frontend is Go with Bubble Tea", "sess-1")
        assert mid1 != mid2
        memories = mem_store.get_memories()
        assert len(memories) == 2

    def test_decay(self, mem_store: MemoryStore) -> None:
        """apply_decay reduces relevance and deletes below threshold."""
        mem_store.save("project_fact", "something", "sess-1")
        # Apply decay many times to push below 0.1
        for _ in range(50):
            mem_store.apply_decay()
        memories = mem_store.get_memories()
        assert len(memories) == 0

    def test_context_budget(self, mem_store: MemoryStore) -> None:
        """get_context respects max_context_tokens budget."""
        for i in range(20):
            content = f"Fact number {i} with enough words to take space"
            mem_store.save("project_fact", content, f"sess-{i}")
        context = mem_store.get_context()
        # 100 tokens * 4 chars/token = 400 chars max
        assert len(context) <= 500  # Some slack for line format

    def test_max_entries(self, mem_store: MemoryStore) -> None:
        """Enforce max_entries retention by pruning lowest relevance."""
        for i in range(15):
            content = f"Unique fact {i} with different words set {i}"
            mem_store.save("project_fact", content, f"sess-{i}")
        memories = mem_store.get_memories(limit=100)
        assert len(memories) <= 10

    def test_delete(self, mem_store: MemoryStore) -> None:
        """Delete a specific memory."""
        mid = mem_store.save("project_fact", "to be deleted", "sess-1")
        assert mem_store.delete(mid)
        assert len(mem_store.get_memories()) == 0
        # Double delete returns False
        assert not mem_store.delete(mid)
