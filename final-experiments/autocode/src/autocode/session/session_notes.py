"""Session Notes for deterministic Path A compaction."""

from __future__ import annotations

from pathlib import Path

ACTIVATION_TOKENS = 10_000
UPDATE_INTERVAL_TOKENS = 5_000
MIN_TOOL_CALLS = 3
DEFAULT_MAX_UPDATE_CHARS = 8_000
SESSION_NOTES_TOOL_ALLOWLIST = ("write_file",)


class SessionNotes:
    """Maintain bounded per-session notes used before LLM compaction."""

    def __init__(
        self,
        *,
        session_id: str,
        base_dir: str | Path,
        max_update_chars: int = DEFAULT_MAX_UPDATE_CHARS,
    ) -> None:
        self.session_id = session_id
        self.base_dir = Path(base_dir).expanduser()
        self.path = self.base_dir / "sessions" / session_id / "SESSION_NOTES.md"
        self.max_update_chars = max_update_chars
        self.last_update_tokens = 0
        self._tool_calls_since_update = 0
        self.allowed_tools = SESSION_NOTES_TOOL_ALLOWLIST

    def record_tool_call(self) -> None:
        self._tool_calls_since_update += 1

    def should_update(self, total_tokens: int) -> bool:
        if total_tokens < ACTIVATION_TOKENS:
            return False
        if self._tool_calls_since_update < MIN_TOOL_CALLS:
            return False
        if self.last_update_tokens == 0:
            return True
        return total_tokens - self.last_update_tokens >= UPDATE_INTERVAL_TOKENS

    def update_from_text(self, text: str, *, total_tokens: int) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        bounded = text[: self.max_update_chars]
        self.path.write_text(bounded, encoding="utf-8")
        self.last_update_tokens = total_tokens
        self._tool_calls_since_update = 0

    def update(self, *, agent_loop: object, total_tokens: int) -> None:
        """Update notes through a bounded write-only updater when available."""
        text = ""
        updater = getattr(agent_loop, "run_session_notes_update", None)
        if callable(updater):
            text = str(
                updater(
                    self.build_update_prompt(agent_loop),
                    allowed_tools=self.allowed_tools,
                    max_output_chars=self.max_update_chars,
                )
                or ""
            )
        if not text:
            text = getattr(agent_loop, "session_summary", "") or getattr(
                agent_loop,
                "_last_compact_summary",
                "",
            )
        if not text:
            text = "Session Notes: no summary available yet."
        self.update_from_text(str(text), total_tokens=total_tokens)

    def build_update_prompt(self, agent_loop: object) -> str:
        objective = getattr(agent_loop, "current_objective", "")
        summary = getattr(agent_loop, "session_summary", "") or getattr(
            agent_loop,
            "_last_compact_summary",
            "",
        )
        return (
            "Update SESSION_NOTES.md for deterministic compaction.\n"
            "Use only the write_file tool. Preserve durable objective, files, "
            "decisions, blockers, and next actions. Do not include raw tool output.\n\n"
            f"Objective: {objective}\n"
            f"Current summary:\n{summary}"
        )[: self.max_update_chars]

    def read_for_compaction(self) -> str:
        try:
            return self.path.read_text(encoding="utf-8")[: self.max_update_chars]
        except OSError:
            return ""
