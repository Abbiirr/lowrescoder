"""Remote compaction — offload context summarization to a separate LLM call.

Based on Codex's codex-api compaction endpoint pattern:
when the context window is filling up, summarize older messages
using a cheap/fast model, freeing tokens for the active conversation.

This is a P2 feature — useful but less urgent than sandbox/policy/middleware.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

COMPACTION_SYSTEM_PROMPT = (
    "You are a conversation summarizer. Summarize the following "
    "conversation history into a concise summary that preserves:\n"
    "1. All file paths and code changes mentioned\n"
    "2. Key decisions and their rationale\n"
    "3. Current task state and what remains to be done\n"
    "4. Any errors encountered and how they were resolved\n\n"
    "Be concise but preserve all actionable information. "
    "Output ONLY the summary, no preamble."
)


@dataclass
class CompactionResult:
    """Result of a remote compaction operation."""

    summary: str
    original_token_count: int
    summary_token_count: int
    messages_compacted: int
    success: bool = True
    error: str = ""

    @property
    def compression_ratio(self) -> float:
        """How much the context was compressed."""
        if self.original_token_count == 0:
            return 0.0
        return 1.0 - (self.summary_token_count / self.original_token_count)


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token)."""
    return len(text) // 4


def format_messages_for_compaction(
    messages: list[dict[str, Any]],
    max_messages: int = 50,
) -> str:
    """Format conversation messages into a compaction prompt."""
    lines: list[str] = []
    for msg in messages[-max_messages:]:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                c.get("text", "") for c in content if isinstance(c, dict)
            )
        # Truncate very long messages
        if len(content) > 2000:
            content = content[:2000] + "...(truncated)"
        lines.append(f"[{role}]: {content}")
    return "\n\n".join(lines)


async def compact_remotely(
    messages: list[dict[str, Any]],
    provider: Any,
    keep_recent: int = 3,
) -> CompactionResult:
    """Compact older messages using a remote LLM call.

    Keeps the most recent `keep_recent` messages intact and
    summarizes everything before them.

    Args:
        messages: Full conversation history
        provider: LLM provider with generate() method
        keep_recent: Number of recent messages to keep verbatim
    """
    if len(messages) <= keep_recent:
        return CompactionResult(
            summary="",
            original_token_count=0,
            summary_token_count=0,
            messages_compacted=0,
        )

    # Split: older messages to compact, recent to keep
    to_compact = messages[:-keep_recent]
    formatted = format_messages_for_compaction(to_compact)
    original_tokens = estimate_tokens(formatted)

    try:
        # Call LLM to summarize
        summary_parts: list[str] = []
        async for chunk in provider.generate([
            {"role": "system", "content": COMPACTION_SYSTEM_PROMPT},
            {"role": "user", "content": formatted},
        ]):
            summary_parts.append(chunk)

        summary = "".join(summary_parts)
        summary_tokens = estimate_tokens(summary)

        return CompactionResult(
            summary=summary,
            original_token_count=original_tokens,
            summary_token_count=summary_tokens,
            messages_compacted=len(to_compact),
        )
    except Exception as e:
        return CompactionResult(
            summary="",
            original_token_count=original_tokens,
            summary_token_count=0,
            messages_compacted=0,
            success=False,
            error=str(e),
        )
