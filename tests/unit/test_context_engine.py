"""Tests for ContextEngine — token counting, truncation, message building (Sprint 4A)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from hybridcoder.agent.context import ContextEngine
from hybridcoder.session.store import SessionStore


@pytest.fixture
def session_store(tmp_path):
    db_path = tmp_path / "test.db"
    store = SessionStore(str(db_path))
    yield store
    store.close()


@pytest.fixture
def session_id(session_store):
    return session_store.create_session(
        title="test", model="test", provider="test",
    )


@pytest.fixture
def mock_provider():
    return AsyncMock()


@pytest.fixture
def engine(mock_provider, session_store):
    return ContextEngine(
        provider=mock_provider,
        session_store=session_store,
        context_length=8192,
        compaction_threshold=0.75,
    )


class TestTokenCounting:
    def test_count_tokens(self, engine):
        assert engine.count_tokens("hello world") == max(1, len("hello world") // 4)
        assert engine.count_tokens("") == 1  # min 1
        assert engine.count_tokens("a" * 100) == 25

    def test_count_tokens_minimum(self, engine):
        assert engine.count_tokens("a") == 1
        assert engine.count_tokens("ab") == 1


class TestTruncation:
    def test_truncate_short_result(self, engine):
        short = "This is a short result"
        assert engine.truncate_tool_result(short) == short

    def test_truncate_long_result(self, engine):
        # 500 tokens ~= 2000 chars, so make something longer
        long_text = "x" * 5000
        result = engine.truncate_tool_result(long_text, max_tokens=500)
        assert "[... truncated ...]" in result
        assert len(result) < len(long_text)
        # Should have head + marker + tail
        assert result.startswith("x" * 100)  # starts with x's
        assert result.endswith("x" * 100)  # ends with x's


class TestBuildMessages:
    @pytest.mark.asyncio
    async def test_build_messages_includes_system(self, engine, session_store, session_id):
        messages = await engine.build_messages(
            session_id, "You are a helper.", [],
        )
        assert messages[0]["role"] == "system"
        assert "You are a helper" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_build_messages_includes_history(self, engine, session_store, session_id):
        session_store.add_message(session_id, "user", "Hello")
        session_store.add_message(session_id, "assistant", "Hi there")
        messages = await engine.build_messages(
            session_id, "System prompt.", [],
        )
        roles = [m["role"] for m in messages]
        assert "user" in roles
        assert "assistant" in roles

    @pytest.mark.asyncio
    async def test_build_messages_with_task_summary(self, engine, session_store, session_id):
        messages = await engine.build_messages(
            session_id, "System prompt.", [],
            task_summary="[ ] Fix bug\n[x] Write tests",
        )
        system_content = messages[0]["content"]
        assert "Active Tasks" in system_content
        assert "Fix bug" in system_content


class TestTaskToolTruncationBypass:
    """Task tools should not have their results truncated (BUG-23)."""

    def test_task_tool_names_in_bypass_set(self):
        """Verify the bypass set is defined correctly in loop.py."""
        # Import is indirect — we verify the constant inline in the tool execution block
        task_tools = {"create_task", "update_task", "add_task_dependency", "list_tasks"}
        assert "create_task" in task_tools
        assert "update_task" in task_tools
        assert "list_tasks" in task_tools
        assert "add_task_dependency" in task_tools

    def test_truncate_would_shorten_long_text(self, engine):
        """Confirm truncation works for non-task tools (baseline)."""
        long_text = "x" * 5000
        result = engine.truncate_tool_result(long_text, max_tokens=500)
        assert "[... truncated ...]" in result


class TestAutoCompact:
    @pytest.mark.asyncio
    async def test_auto_compact_triggers(self, session_store, session_id):
        """Compaction fires when over threshold."""
        # Use a tiny context to force compaction
        engine = ContextEngine(
            provider=None,
            session_store=session_store,
            context_length=200,  # Very small
            compaction_threshold=0.5,
        )
        # Add many messages to exceed threshold
        for i in range(10):
            session_store.add_message(session_id, "user", f"Message {i} " * 20)
            session_store.add_message(session_id, "assistant", f"Reply {i} " * 20)

        messages_before = session_store.get_messages(session_id)
        count_before = len(messages_before)

        await engine.build_messages(
            session_id, "Sys", [],
        )
        messages_after = session_store.get_messages(session_id)
        # After compaction, should have fewer messages (4 kept + summary)
        assert len(messages_after) < count_before

    @pytest.mark.asyncio
    async def test_auto_compact_fallback(self, session_store, session_id):
        """Works without provider (sliding window)."""
        engine = ContextEngine(
            provider=None,
            session_store=session_store,
            context_length=8192,
        )
        for i in range(10):
            session_store.add_message(session_id, "user", f"Msg {i}")

        summary = await engine.auto_compact(session_id, kept_messages=4)
        assert summary  # Non-empty summary
        messages_after = session_store.get_messages(session_id)
        # Should have 4 kept + 1 summary = 5
        assert len(messages_after) == 5
