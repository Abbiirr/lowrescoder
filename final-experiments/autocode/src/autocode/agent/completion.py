"""Session completion summary statistics."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from autocode.agent.profiler import Profiler
from autocode.agent.token_tracker import TokenTracker


@dataclass
class SessionStats:
    """Tracks session-level statistics for completion summary."""

    start_time: float = field(default_factory=time.monotonic)
    files_changed: list[str] = field(default_factory=list)
    tools_used: dict[str, int] = field(default_factory=dict)
    token_tracker: TokenTracker = field(default_factory=TokenTracker)
    profiler: Profiler | None = None

    def record_file_change(self, path: str) -> None:
        """Record a file that was modified."""
        if path not in self.files_changed:
            self.files_changed.append(path)

    def record_tool_use(self, tool_name: str) -> None:
        """Record a tool invocation."""
        self.tools_used[tool_name] = self.tools_used.get(tool_name, 0) + 1

    @property
    def elapsed_seconds(self) -> float:
        """Time elapsed since session start."""
        return time.monotonic() - self.start_time

    def summary(self) -> str:
        """Generate a human-readable completion summary."""
        elapsed = self.elapsed_seconds
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)

        parts = ["Session Summary", "-" * 30]

        # Time
        if minutes > 0:
            parts.append(f"Time: {minutes}m {seconds}s")
        else:
            parts.append(f"Time: {seconds}s")

        # Tokens
        tokens = self.token_tracker.total
        if tokens.total_tokens > 0:
            parts.append(
                f"Tokens: {tokens.total_tokens:,} "
                f"(prompt: {tokens.prompt_tokens:,}, "
                f"completion: {tokens.completion_tokens:,})"
            )
            parts.append(f"API calls: {self.token_tracker.call_count}")

        # Files
        if self.files_changed:
            parts.append(f"Files changed: {len(self.files_changed)}")
            for f in self.files_changed[:10]:
                parts.append(f"  - {f}")
            if len(self.files_changed) > 10:
                parts.append(f"  ... and {len(self.files_changed) - 10} more")
        else:
            parts.append("Files changed: 0")

        # Tools
        if self.tools_used:
            tool_summary = ", ".join(
                f"{name}({count})"
                for name, count in sorted(
                    self.tools_used.items(),
                    key=lambda x: -x[1],
                )[:5]
            )
            total_calls = sum(self.tools_used.values())
            parts.append(f"Tool calls: {total_calls} ({tool_summary})")

        if self.profiler and self.profiler.entries:
            cats = self.profiler.by_category()
            if cats.get("llm"):
                parts.append(
                    "LLM latency: "
                    f"p50 {self.profiler.p50('llm'):.0f}ms, "
                    f"p95 {self.profiler.p95('llm'):.0f}ms"
                )
            if cats.get("tool"):
                parts.append(
                    "Tool latency: "
                    f"p50 {self.profiler.p50('tool'):.0f}ms, "
                    f"p95 {self.profiler.p95('tool'):.0f}ms"
                )

        return "\n".join(parts)
