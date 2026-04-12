"""Context engine for token budget management and auto-compaction."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from autocode.session.consolidation import SessionConsolidator
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
        """MicroCompact: truncate tool output from the middle.

        Keeps head (first ~60%) and tail (last ~40%) since useful info
        like stack traces clusters at beginning and end. No API call needed.
        """
        token_count = self.count_tokens(result)
        if token_count <= max_tokens:
            return result

        max_chars = max_tokens * 4
        head_chars = int(max_chars * 0.6)
        tail_chars = max_chars - head_chars
        omitted = len(result) - head_chars - tail_chars
        return (
            result[:head_chars]
            + f"\n\n[… {omitted} chars omitted …]\n\n"
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
        before_compaction: Callable[[], bool] | None = None,
        after_compaction: Callable[[str], None] | None = None,
        static_prefix: str | None = None,
        dynamic_suffix: str | None = None,
    ) -> list[dict[str, Any]]:
        """Assemble messages for the LLM, triggering compaction if needed.

        Args:
            session_id: The current session ID.
            system_prompt: Base system prompt text (used when static/dynamic
                split is not provided).
            tool_schemas: Tool schemas (for budget estimation).
            memory_context: Memory context to inject into system prompt.
            task_summary: Task summary to inject into system prompt.
            subagent_status: Subagent status to inject into system prompt.
            static_prefix: Cacheable static portion of the system prompt.
                When provided with dynamic_suffix, the system message is
                split into two content blocks with cache_control on the
                static part.
            dynamic_suffix: Dynamic portion of the system prompt (changes
                each iteration).

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

        # Auto-compact if over threshold (Tier 2: AutoCompact at 75%)
        threshold_tokens = int(budget * self._compaction_threshold)
        if total_msg_tokens > threshold_tokens and len(stored_messages) > 4:
            should_compact = True
            if before_compaction is not None:
                should_compact = before_compaction()
            if should_compact:
                summary = await self.auto_compact(session_id)
                if after_compaction is not None:
                    after_compaction(summary)
                stored_messages = self._session_store.get_messages(session_id)
                total_msg_tokens = sum(
                    self.count_tokens(m.content) for m in stored_messages
                )

        # Emergency FullCompact (Tier 3: at 90% — keep only last 2 messages)
        emergency_tokens = int(budget * 0.90)
        if total_msg_tokens > emergency_tokens and len(stored_messages) > 2:
            logger.warning(
                "FullCompact: %d tokens > %d emergency threshold, aggressive trim",
                total_msg_tokens,
                emergency_tokens,
            )
            summary = await self.auto_compact(session_id, kept_messages=2)
            if after_compaction is not None:
                after_compaction(summary)
            stored_messages = self._session_store.get_messages(session_id)

        # Assemble final message list
        # When static/dynamic split is provided, use two content blocks
        # with cache_control on the static part to enable prompt caching.
        if static_prefix is not None and dynamic_suffix is not None:
            messages: list[dict[str, Any]] = [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": static_prefix,
                            "cache_control": {"type": "ephemeral"},
                        },
                        {
                            "type": "text",
                            "text": dynamic_suffix,
                        },
                    ],
                },
            ]
        else:
            messages = [
                {"role": "system", "content": full_system},
            ]
        for msg in stored_messages:
            if msg.role in ("user", "assistant", "system", "tool"):
                messages.append({"role": msg.role, "content": msg.content})

        return messages

    async def auto_compact(
        self,
        session_id: str,
        kept_messages: int = 4,
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
        old_conversation = self._session_store.get_messages_with_tool_calls(
            session_id,
        )[:-kept_messages]

        # Try to summarize with the provider
        summary = ""
        if self._provider is not None and hasattr(self._provider, "generate"):
            try:
                summary_parts = [f"{m.role}: {m.content[:200]}" for m in old_messages]
                summary_text = "\n".join(summary_parts)
                # Use proper message format (list[dict]) and consume stream
                messages_for_provider = [
                    {
                        "role": "system",
                        "content": (
                            "Summarize this conversation concisely. Preserve key "
                            "decisions, file paths, and action items."
                        ),
                    },
                    {"role": "user", "content": summary_text},
                ]
                chunks: list[str] = []
                async for chunk in self._provider.generate(messages_for_provider):
                    chunks.append(chunk)
                summary = "".join(chunks)
            except Exception:
                logger.debug("Provider summarization failed, using fallback")
                summary = ""

        # Fallback: simple text summary
        if not summary:
            consolidator = SessionConsolidator()
            summary = consolidator.build_carry_forward_summary(old_conversation)

        self._session_store.compact_session(
            session_id,
            summary=summary,
            kept_messages=kept_messages,
        )
        logger.debug("Auto-compacted session %s, kept %d messages", session_id, kept_messages)
        return summary


# --- Four-Plane Context Model ---
# Formalized per PLAN.md Section 0.1


class ContextPlane(Enum):
    """The four context planes in AutoCode.

    - DURABLE_INSTRUCTIONS: Policy, system prompts, agent rules (~2KB budget)
    - DURABLE_MEMORY: Learned project facts (~10KB budget)
    - LIVE_SESSION: Current task state (~50KB budget)
    - EPHEMERAL: Per-turn scratch (~5KB budget, always discarded)
    """

    DURABLE_INSTRUCTIONS = auto()
    DURABLE_MEMORY = auto()
    LIVE_SESSION = auto()
    EPHEMERAL = auto()


@dataclass
class PlaneBudget:
    """Budget limits per plane (in tokens, estimated at ~4 chars/token)."""

    durable_instructions: int = 512
    durable_memory: int = 2560
    live_session: int = 12800
    ephemeral: int = 1280

    def get_limit(self, plane: ContextPlane) -> int:
        """Get the budget limit for a given plane."""
        if plane == ContextPlane.DURABLE_INSTRUCTIONS:
            return self.durable_instructions
        if plane == ContextPlane.DURABLE_MEMORY:
            return self.durable_memory
        if plane == ContextPlane.LIVE_SESSION:
            return self.live_session
        return self.ephemeral


@dataclass
class PlaneState:
    """Tracks current state within a context plane."""

    plane: ContextPlane
    token_count: int
    compacted: bool = False
    last_compaction: str | None = None


def get_plane_for_content(content: str, is_durable: bool = False) -> ContextPlane:
    """Classify content into the appropriate context plane.

    Args:
        content: The content to classify.
        is_durable: Whether this content should persist beyond the session.

    Returns:
        The appropriate ContextPlane for this content.
    """
    if is_durable or _is_policy_content(content):
        return ContextPlane.DURABLE_INSTRUCTIONS
    if _is_learned_fact(content):
        return ContextPlane.DURABLE_MEMORY
    if _is_session_transient(content):
        return ContextPlane.LIVE_SESSION
    return ContextPlane.EPHEMERAL


def _is_policy_content(content: str) -> bool:
    """Check if content is policy/instruction type."""
    # More precise: must be at start of word or followed by punctuation
    content_lower = content[:500].lower()
    return (
        "agent" in content_lower
        or content_lower.startswith("claude")
        or content_lower.startswith("instructions")
        or content_lower.startswith("system ")
        or "prompt" in content_lower
        or "rules" in content_lower
        and ":" in content_lower[:100]
    )


def _is_learned_fact(content: str) -> bool:
    """Check if content is a learned project fact."""
    markers = ("learned", "pattern", "gotcha", "project_fact", "architecture")
    return any(m in content.lower() for m in markers)


def _is_session_transient(content: str) -> bool:
    """Check if content is session-scoped transient."""
    markers = ("tool_call", "result", "error", "search_hits", "working_set")
    return any(m in content.lower() for m in markers)


# --- Canonical Runtime State (PLAN.md Section 0.3) ---
# One authoritative shape for all shared runtime state


@dataclass
class RuntimeState:
    """Canonical runtime state owned by the Orchestrator.

    Per PLAN.md Section 0.3, this unifies state that was previously
    scattered across loop, frontend, and orchestrator.
    """

    session_id: str = ""
    task_id: str = ""
    approval_mode: str = "suggest"
    agent_mode: str = "normal"
    project_root: str = ""
    working_set: list[str] = field(default_factory=list)
    checkpoint_stack: list[str] = field(default_factory=list)
    pending_approvals: list[str] = field(default_factory=list)
    subagent_registry: list[str] = field(default_factory=list)
    current_plan_ref: str = ""
    last_compact_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for state transfer."""
        return {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "approval_mode": self.approval_mode,
            "agent_mode": self.agent_mode,
            "project_root": self.project_root,
            "working_set": list(self.working_set),
            "checkpoint_stack": list(self.checkpoint_stack),
            "pending_approvals": list(self.pending_approvals),
            "subagent_registry": list(self.subagent_registry),
            "current_plan_ref": self.current_plan_ref,
            "last_compact_summary": self.last_compact_summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuntimeState:
        """Deserialize from dict."""
        return cls(
            session_id=data.get("session_id", ""),
            task_id=data.get("task_id", ""),
            approval_mode=data.get("approval_mode", "suggest"),
            agent_mode=data.get("agent_mode", "normal"),
            project_root=data.get("project_root", ""),
            working_set=list(data.get("working_set", [])),
            checkpoint_stack=list(data.get("checkpoint_stack", [])),
            pending_approvals=list(data.get("pending_approvals", [])),
            subagent_registry=list(data.get("subagent_registry", [])),
            current_plan_ref=data.get("current_plan_ref", ""),
            last_compact_summary=data.get("last_compact_summary", ""),
        )
