"""Context engine for token budget management and auto-compaction."""

from __future__ import annotations

import logging
from typing import Any

from autocode.session.store import SessionStore

logger = logging.getLogger(__name__)


class ContextEngine:
    """Manages context window budget, message assembly, and auto-compaction.

    Provides token counting (heuristic), result truncation, and automatic
    compaction when the context window approaches its limit.
    """

    def __init__(
        self,
        provider: Any,
        session_store: SessionStore,
        context_length: int = 8192,
        compaction_threshold: float = 0.75,
    ) -> None:
        self._provider = provider
        self._session_store = session_store
        self._context_length = context_length
        self._compaction_threshold = compaction_threshold

    def count_tokens(self, text: str) -> int:
        """Estimate token count using a simple heuristic (len // 4)."""
        return max(1, len(text) // 4)

    def truncate_tool_result(self, result: str, max_tokens: int = 500) -> str:
        """Truncate a tool result if it exceeds max_tokens.

        Keeps the first ~200 tokens and last ~100 tokens with a marker.
        """
        token_count = self.count_tokens(result)
        if token_count <= max_tokens:
            return result

        head_chars = 200 * 4
        tail_chars = 100 * 4
        return (
            result[:head_chars]
            + "\n[... truncated ...]\n"
            + result[-tail_chars:]
        )

    async def build_messages(
        self,
        session_id: str,
        system_prompt: str,
        tool_schemas: list[dict[str, Any]],
        *,
        memory_context: str = "",
        task_summary: str = "",
        subagent_status: str = "",
    ) -> list[dict[str, Any]]:
        """Assemble messages for the LLM, triggering compaction if needed.

        Args:
            session_id: The current session ID.
            system_prompt: Base system prompt text.
            tool_schemas: Tool schemas (for budget estimation).
            memory_context: Memory context to inject into system prompt.
            task_summary: Task summary to inject into system prompt.
            subagent_status: Subagent status to inject into system prompt.

        Returns:
            List of message dicts ready for the LLM provider.
        """
        # Build enhanced system prompt with injected sections
        full_system = system_prompt
        if task_summary:
            full_system += f"\n## Active Tasks\n{task_summary}\n"
        if memory_context:
            full_system += f"\n## Memory\n{memory_context}\n"
        if subagent_status:
            full_system += f"\n## Subagent Status\n{subagent_status}\n"

        # Estimate budget
        system_tokens = self.count_tokens(full_system)
        schema_tokens = self.count_tokens(str(tool_schemas))
        overhead = system_tokens + schema_tokens
        budget = self._context_length - overhead

        # Get messages from store
        stored_messages = self._session_store.get_messages(session_id)

        # Estimate total message tokens
        total_msg_tokens = sum(self.count_tokens(m.content) for m in stored_messages)

        # Auto-compact if over threshold
        threshold_tokens = int(budget * self._compaction_threshold)
        if total_msg_tokens > threshold_tokens and len(stored_messages) > 4:
            await self.auto_compact(session_id)
            stored_messages = self._session_store.get_messages(session_id)

        # Assemble final message list
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": full_system},
        ]
        for msg in stored_messages:
            if msg.role in ("user", "assistant", "system", "tool"):
                messages.append({"role": msg.role, "content": msg.content})

        return messages

    async def auto_compact(
        self, session_id: str, kept_messages: int = 4,
    ) -> str:
        """Compact older messages, keeping only the most recent ones.

        Attempts to use the provider to summarize old messages. Falls back
        to a simple sliding window (drop oldest beyond kept_messages).

        Returns:
            The summary text that was generated.
        """
        messages = self._session_store.get_messages(session_id)
        if len(messages) <= kept_messages:
            return ""

        old_messages = messages[:-kept_messages]

        # Try to summarize with the provider
        summary = ""
        if self._provider is not None and hasattr(self._provider, "generate"):
            try:
                summary_parts = [
                    f"{m.role}: {m.content[:200]}" for m in old_messages
                ]
                summary_prompt = (
                    "Summarize this conversation concisely:\n"
                    + "\n".join(summary_parts)
                )
                response = await self._provider.generate(summary_prompt)
                summary = getattr(response, "content", "") or str(response)
            except Exception:
                logger.debug("Provider summarization failed, using fallback")
                summary = ""

        # Fallback: simple text summary
        if not summary:
            summary_parts = [
                f"{m.role}: {m.content[:100]}" for m in old_messages
            ]
            summary = "Summary of previous conversation:\n" + "\n".join(summary_parts)

        self._session_store.compact_session(
            session_id, summary=summary, kept_messages=kept_messages,
        )
        logger.debug("Auto-compacted session %s, kept %d messages", session_id, kept_messages)
        return summary
