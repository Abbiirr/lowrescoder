"""Performance profiler — measure latency of critical paths.

Profiles tool execution, LLM calls, and context operations
to identify optimization opportunities.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TimingEntry:
    """A single timing measurement."""

    name: str
    duration_ms: float
    category: str = ""  # "llm", "tool", "context", "io"
    metadata: dict[str, Any] = field(default_factory=dict)


class Profiler:
    """Collects timing measurements for performance analysis."""

    def __init__(self) -> None:
        self._entries: list[TimingEntry] = []
        self._active: dict[str, float] = {}

    def start(self, name: str) -> None:
        """Start timing an operation."""
        self._active[name] = time.monotonic()

    def stop(self, name: str, category: str = "", **metadata: Any) -> float:
        """Stop timing and record. Returns duration in ms."""
        start = self._active.pop(name, None)
        if start is None:
            return 0.0
        duration_ms = (time.monotonic() - start) * 1000
        self._entries.append(TimingEntry(
            name=name,
            duration_ms=duration_ms,
            category=category,
            metadata=metadata,
        ))
        return duration_ms

    def measure(self, name: str, category: str = "") -> _TimingContext:
        """Context manager for timing a block."""
        return _TimingContext(self, name, category)

    @property
    def entries(self) -> list[TimingEntry]:
        return list(self._entries)

    def by_category(self) -> dict[str, list[TimingEntry]]:
        """Group entries by category."""
        result: dict[str, list[TimingEntry]] = {}
        for e in self._entries:
            result.setdefault(e.category or "other", []).append(e)
        return result

    def p50(self, category: str = "") -> float:
        """Median latency for a category (ms)."""
        entries = [e for e in self._entries if not category or e.category == category]
        if not entries:
            return 0.0
        durations = sorted(e.duration_ms for e in entries)
        return durations[len(durations) // 2]

    def p95(self, category: str = "") -> float:
        """95th percentile latency for a category (ms)."""
        entries = [e for e in self._entries if not category or e.category == category]
        if not entries:
            return 0.0
        durations = sorted(e.duration_ms for e in entries)
        idx = int(len(durations) * 0.95)
        return durations[min(idx, len(durations) - 1)]

    def total_ms(self, category: str = "") -> float:
        """Total time spent in a category (ms)."""
        return sum(
            e.duration_ms for e in self._entries
            if not category or e.category == category
        )

    def summary(self) -> str:
        """Human-readable performance summary."""
        lines = ["Performance Profile", "=" * 40]
        lines.append(f"Total measurements: {len(self._entries)}")

        for cat, entries in sorted(self.by_category().items()):
            total = sum(e.duration_ms for e in entries)
            avg = total / len(entries) if entries else 0
            lines.append(f"\n{cat} ({len(entries)} calls):")
            lines.append(f"  Total: {total:.0f}ms")
            lines.append(f"  Avg: {avg:.0f}ms")
            lines.append(f"  p50: {self.p50(cat):.0f}ms")
            lines.append(f"  p95: {self.p95(cat):.0f}ms")

        return "\n".join(lines)

    def reset(self) -> None:
        """Clear all measurements."""
        self._entries.clear()
        self._active.clear()


class _TimingContext:
    """Context manager for profiler.measure()."""

    def __init__(self, profiler: Profiler, name: str, category: str) -> None:
        self._profiler = profiler
        self._name = name
        self._category = category

    def __enter__(self) -> _TimingContext:
        self._profiler.start(self._name)
        return self

    def __exit__(self, *args: Any) -> None:
        self._profiler.stop(self._name, self._category)
