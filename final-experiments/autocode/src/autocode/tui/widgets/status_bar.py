"""Status bar widget showing model, mode, and token count."""

from __future__ import annotations

from typing import Any

from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import Static


class StatusBar(Static):
    """Bottom status bar with model/mode/token info."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    model: reactive[str] = reactive("qwen3:8b")
    mode: reactive[str] = reactive("suggest")
    tokens: reactive[int] = reactive(0)
    thinking: reactive[bool] = reactive(False)
    user_typing: reactive[bool] = reactive(False)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._dot_tick: int = 0
        self._dot_timer: Timer | None = None

    def watch_thinking(self, value: bool) -> None:
        """Start/stop animated dots when thinking state changes."""
        if value:
            self._dot_tick = 0
            self._dot_timer = self.set_interval(0.5, self._animate_dots)
        elif self._dot_timer is not None:
            self._dot_timer.stop()
            self._dot_timer = None
            self._dot_tick = 0

    def _animate_dots(self) -> None:
        """Advance the thinking dots animation."""
        self._dot_tick += 1
        self.refresh()

    def render(self) -> str:
        parts = [f"Model: {self.model}", f"Mode: {self.mode}", f"Tokens: {self.tokens}"]
        if self.thinking:
            dots = "." * ((self._dot_tick % 3) + 1)
            parts.insert(0, f"Thinking{dots}")
        if self.user_typing:
            parts.append("You: typing...")
        return " " + " | ".join(parts)
