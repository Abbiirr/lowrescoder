"""Tests for token counting and accumulation."""

from __future__ import annotations

from autocode.agent.token_tracker import TokenTracker, TokenUsage


def test_token_usage_total() -> None:
    """TokenUsage.total_tokens sums prompt + completion."""
    usage = TokenUsage(prompt_tokens=100, completion_tokens=50)
    assert usage.total_tokens == 150


def test_token_count_accumulates() -> None:
    """Token counts add up across multiple API calls."""
    tracker = TokenTracker()
    tracker.record(prompt_tokens=100, completion_tokens=50)
    tracker.record(prompt_tokens=200, completion_tokens=75)
    tracker.record(prompt_tokens=150, completion_tokens=60)

    assert tracker.total.prompt_tokens == 450
    assert tracker.total.completion_tokens == 185
    assert tracker.total.total_tokens == 635
    assert tracker.call_count == 3


def test_token_count_displays_in_summary() -> None:
    """Token count appears in session summary."""
    tracker = TokenTracker()
    tracker.record(prompt_tokens=1000, completion_tokens=500)
    tracker.record(prompt_tokens=2000, completion_tokens=800)

    summary = tracker.summary()
    assert "4,300" in summary  # total (3000+1300)
    assert "3,000" in summary  # prompt
    assert "1,300" in summary  # completion
    assert "API calls: 2" in summary


def test_token_count_per_provider() -> None:
    """Separate counts for L3 vs L4 providers."""
    tracker = TokenTracker()
    tracker.record(prompt_tokens=100, completion_tokens=50, provider="ollama_l4")
    tracker.record(prompt_tokens=200, completion_tokens=75, provider="llama_cpp_l3")
    tracker.record(prompt_tokens=150, completion_tokens=60, provider="ollama_l4")

    l4 = tracker.by_provider("ollama_l4")
    assert l4.prompt_tokens == 250
    assert l4.completion_tokens == 110

    l3 = tracker.by_provider("llama_cpp_l3")
    assert l3.prompt_tokens == 200
    assert l3.completion_tokens == 75

    assert tracker.total.total_tokens == 635
    assert set(tracker.providers) == {"ollama_l4", "llama_cpp_l3"}


def test_token_count_unknown_provider() -> None:
    """Querying unknown provider returns zero usage."""
    tracker = TokenTracker()
    tracker.record(prompt_tokens=100, completion_tokens=50)

    unknown = tracker.by_provider("nonexistent")
    assert unknown.total_tokens == 0


def test_token_tracker_reset() -> None:
    """Reset clears all counters."""
    tracker = TokenTracker()
    tracker.record(prompt_tokens=100, completion_tokens=50, provider="test")
    tracker.reset()

    assert tracker.total.total_tokens == 0
    assert tracker.call_count == 0
    assert tracker.providers == []


def test_token_summary_multi_provider() -> None:
    """Summary shows per-provider breakdown when multiple providers used."""
    tracker = TokenTracker()
    tracker.record(prompt_tokens=500, completion_tokens=200, provider="ollama")
    tracker.record(prompt_tokens=300, completion_tokens=100, provider="openrouter")

    summary = tracker.summary()
    assert "ollama:" in summary
    assert "openrouter:" in summary
