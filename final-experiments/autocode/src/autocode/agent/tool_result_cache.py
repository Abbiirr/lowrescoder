"""Tool-result clearing primitive (deep-research-report Phase B Item 2).

The deep-research report calls out **tool-result clearing** as a
first-class context engineering primitive: when the agent has called
``read_file`` or ``search_text`` 20 times during a long turn, the
cached tool results dominate the prompt even though most of them are
stale. The ``compaction`` pipeline can remove them wholesale, but there
was no **selective** "drop just this set of results" primitive.

This module ships:

- :class:`ToolResultCache` — a bounded LRU-style cache keyed by
  ``(tool, args_hash)`` with values being the text result and
  metadata.
- :meth:`ToolResultCache.clear` — remove specific entries by id, by
  tool name, by age, or all at once.
- :meth:`ToolResultCache.summary` — a structured rundown the agent
  can read when deciding *which* entries to clear.

The cache is intentionally per-turn (or per-session) — it's a working
buffer, not durable memory. Durable memory goes through
``session/consolidation.py``.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field


@dataclass
class ToolResultEntry:
    """A cached tool-call result with audit metadata."""

    id: str
    tool: str
    args_hash: str
    args_preview: str
    result: str
    created_at: float
    size_bytes: int
    cleared: bool = False


@dataclass
class ToolResultCache:
    """Bounded cache of recent tool-call results with a clear primitive.

    Not thread-safe — intended to be owned by a single agent loop.
    """

    max_entries: int = 100
    max_total_bytes: int = 256 * 1024  # 256 KB
    entries: list[ToolResultEntry] = field(default_factory=list)
    _next_id: int = 1

    def record(self, tool: str, args: dict | str, result: str) -> str:
        """Add a result to the cache. Returns the assigned id.

        Evicts the oldest non-cleared entry when the cache is full.
        """
        args_repr: str
        if isinstance(args, dict):
            try:
                args_repr = json.dumps(args, sort_keys=True, default=str)
            except (TypeError, ValueError):
                args_repr = repr(args)
        else:
            args_repr = str(args)
        args_hash = hashlib.sha1(
            f"{tool}:{args_repr}".encode("utf-8")
        ).hexdigest()[:12]
        preview = args_repr if len(args_repr) <= 80 else args_repr[:77] + "..."

        entry = ToolResultEntry(
            id=f"tr{self._next_id:04d}",
            tool=tool,
            args_hash=args_hash,
            args_preview=preview,
            result=result,
            created_at=time.time(),
            size_bytes=len(result.encode("utf-8", errors="replace")),
            cleared=False,
        )
        self._next_id += 1
        self.entries.append(entry)
        self._enforce_budget()
        return entry.id

    def _enforce_budget(self) -> None:
        """Evict oldest non-cleared entries until budget is satisfied."""
        # Drop truly over-count
        while len(self.entries) > self.max_entries:
            self.entries.pop(0)
        # Then drop until bytes fit — only count non-cleared entries
        total = sum(e.size_bytes for e in self.entries if not e.cleared)
        while total > self.max_total_bytes and self.entries:
            victim = None
            for e in self.entries:
                if not e.cleared:
                    victim = e
                    break
            if victim is None:
                break
            total -= victim.size_bytes
            self.entries.remove(victim)

    def clear(
        self,
        *,
        ids: list[str] | None = None,
        tool: str | None = None,
        older_than_seconds: float | None = None,
        all: bool = False,
    ) -> int:
        """Mark entries as cleared. Returns the count cleared.

        Modes (apply in priority order):

        - ``all=True`` clears every entry.
        - ``ids=[...]`` clears specific entries by id.
        - ``tool="read_file"`` clears every entry with that tool name.
        - ``older_than_seconds=300`` clears entries older than 5 min.

        Cleared entries stay in the list (so the agent can audit what
        was cleared) but their ``cleared`` flag is True and they should
        be excluded from the rendered tool-result window.
        """
        cleared_count = 0

        if all:
            for e in self.entries:
                if not e.cleared:
                    e.cleared = True
                    cleared_count += 1
            return cleared_count

        id_set = set(ids or [])
        now = time.time()
        for e in self.entries:
            if e.cleared:
                continue
            match = False
            if id_set and e.id in id_set:
                match = True
            elif tool is not None and e.tool == tool:
                match = True
            elif (
                older_than_seconds is not None
                and (now - e.created_at) > older_than_seconds
            ):
                match = True
            if match:
                e.cleared = True
                cleared_count += 1

        return cleared_count

    def live_entries(self) -> list[ToolResultEntry]:
        """Return only the non-cleared entries (what the prompt should see)."""
        return [e for e in self.entries if not e.cleared]

    def summary(self) -> str:
        """Human/LLM-readable summary of the cache state."""
        if not self.entries:
            return "Tool result cache: empty."

        live = self.live_entries()
        total_live_bytes = sum(e.size_bytes for e in live)
        cleared_count = sum(1 for e in self.entries if e.cleared)

        lines = [
            f"Tool result cache: {len(live)} live, {cleared_count} cleared, "
            f"{total_live_bytes} bytes",
        ]
        for e in live[:20]:
            marker = " "
            lines.append(
                f" {marker}{e.id}  {e.tool:14s}  "
                f"{e.size_bytes:6d}B  {e.args_preview}"
            )
        if len(live) > 20:
            lines.append(f"  ... and {len(live) - 20} more live entries")
        return "\n".join(lines)
