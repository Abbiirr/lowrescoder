"""Tests for performance profiler."""

from __future__ import annotations

import time

from autocode.agent.profiler import Profiler


def test_start_stop() -> None:
    """Basic start/stop timing."""
    p = Profiler()
    p.start("test_op")
    time.sleep(0.01)
    ms = p.stop("test_op", category="tool")
    assert ms > 5  # at least 5ms
    assert len(p.entries) == 1
    assert p.entries[0].category == "tool"


def test_context_manager() -> None:
    """Timing via context manager."""
    p = Profiler()
    with p.measure("block", category="llm"):
        time.sleep(0.01)
    assert len(p.entries) == 1
    assert p.entries[0].duration_ms > 5


def test_by_category() -> None:
    """Group entries by category."""
    p = Profiler()
    p.start("a"); p.stop("a", "llm")
    p.start("b"); p.stop("b", "tool")
    p.start("c"); p.stop("c", "llm")

    cats = p.by_category()
    assert len(cats["llm"]) == 2
    assert len(cats["tool"]) == 1


def test_percentiles() -> None:
    """p50 and p95 calculations."""
    p = Profiler()
    for i in range(20):
        p.start(f"op_{i}")
        p.stop(f"op_{i}", "test")

    assert p.p50("test") >= 0
    assert p.p95("test") >= p.p50("test")


def test_total_ms() -> None:
    """Total time per category."""
    p = Profiler()
    p.start("a"); time.sleep(0.01); p.stop("a", "llm")
    p.start("b"); time.sleep(0.01); p.stop("b", "tool")

    assert p.total_ms("llm") > 5
    assert p.total_ms("tool") > 5
    assert p.total_ms() > 10  # all categories


def test_summary() -> None:
    """Summary contains key metrics."""
    p = Profiler()
    p.start("op"); p.stop("op", "llm")
    s = p.summary()
    assert "Performance Profile" in s
    assert "llm" in s
    assert "p50" in s


def test_reset() -> None:
    """Reset clears all data."""
    p = Profiler()
    p.start("x"); p.stop("x")
    p.reset()
    assert len(p.entries) == 0


def test_stop_without_start() -> None:
    """Stop without start returns 0."""
    p = Profiler()
    ms = p.stop("nonexistent")
    assert ms == 0.0
