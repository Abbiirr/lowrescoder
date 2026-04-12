"""Tests for session completion summary."""

from __future__ import annotations

from autocode.agent.completion import SessionStats
from autocode.agent.profiler import Profiler


def test_on_done_has_summary_stats() -> None:
    """on_done output includes files changed, time elapsed."""
    stats = SessionStats()
    stats.record_file_change("src/app.py")
    stats.record_file_change("src/utils.py")
    stats.record_tool_use("read_file")
    stats.record_tool_use("write_file")
    stats.record_tool_use("read_file")

    summary = stats.summary()
    assert "Files changed: 2" in summary
    assert "src/app.py" in summary
    assert "Tool calls: 3" in summary
    assert "read_file(2)" in summary
    assert "Time:" in summary


def test_on_done_has_token_count() -> None:
    """on_done output includes token usage."""
    stats = SessionStats()
    stats.token_tracker.record(prompt_tokens=500, completion_tokens=200)
    stats.token_tracker.record(prompt_tokens=300, completion_tokens=100)

    summary = stats.summary()
    assert "1,100" in summary  # total
    assert "800" in summary  # prompt
    assert "300" in summary  # completion
    assert "API calls: 2" in summary


def test_on_done_empty_session() -> None:
    """Empty session produces minimal summary."""
    stats = SessionStats()
    summary = stats.summary()
    assert "Files changed: 0" in summary
    assert "Session Summary" in summary


def test_on_done_includes_profiler_latencies() -> None:
    """Profiler-backed summaries expose p50/p95 latency lines."""
    stats = SessionStats()
    stats.profiler = Profiler()
    stats.profiler.start("llm-1")
    stats.profiler.stop("llm-1", "llm")
    stats.profiler.start("tool-1")
    stats.profiler.stop("tool-1", "tool")

    summary = stats.summary()
    assert "LLM latency:" in summary
    assert "Tool latency:" in summary
