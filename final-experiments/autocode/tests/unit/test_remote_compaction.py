"""Tests for remote compaction."""

from __future__ import annotations

from autocode.agent.remote_compaction import (
    CompactionResult,
    estimate_tokens,
    format_messages_for_compaction,
)


def test_estimate_tokens() -> None:
    """Token estimation is roughly 4 chars per token."""
    assert estimate_tokens("hello world") == 2  # 11 chars / 4
    assert estimate_tokens("a" * 400) == 100


def test_format_messages() -> None:
    """Format preserves role and content."""
    messages = [
        {"role": "user", "content": "Fix the bug"},
        {"role": "assistant", "content": "I'll look at it"},
    ]
    result = format_messages_for_compaction(messages)
    assert "[user]: Fix the bug" in result
    assert "[assistant]: I'll look at it" in result


def test_format_truncates_long_messages() -> None:
    """Long messages are truncated."""
    messages = [{"role": "user", "content": "x" * 5000}]
    result = format_messages_for_compaction(messages)
    assert len(result) < 5000
    assert "truncated" in result


def test_compaction_result_compression_ratio() -> None:
    """Compression ratio calculated correctly."""
    result = CompactionResult(
        summary="short",
        original_token_count=1000,
        summary_token_count=200,
        messages_compacted=10,
    )
    assert result.compression_ratio == 0.8  # 80% compression


def test_compaction_result_zero_original() -> None:
    """Zero original tokens gives 0 ratio."""
    result = CompactionResult(
        summary="", original_token_count=0,
        summary_token_count=0, messages_compacted=0,
    )
    assert result.compression_ratio == 0.0


def test_format_handles_list_content() -> None:
    """Format handles messages with list content (multimodal)."""
    messages = [
        {"role": "user", "content": [
            {"type": "text", "text": "Look at this code"},
        ]},
    ]
    result = format_messages_for_compaction(messages)
    assert "Look at this code" in result
