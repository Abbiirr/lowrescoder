"""Input bar widget for user text entry."""

from __future__ import annotations

from pathlib import Path

from textual import events
from textual.message import Message
from textual.widgets import TextArea


class InputBar(TextArea):
    """Text input with Enter to submit, Shift+Enter for newline, Up/Down for history."""

    DEFAULT_CSS = """
    InputBar {
        height: auto;
        max-height: 8;
        min-height: 3;
        margin: 0 1;
        border: solid $accent;
    }
    InputBar:focus {
        border: solid $accent-lighten-2;
    }
    """

    class Submitted(Message):
        """Posted when the user presses Enter to submit."""

        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    def __init__(self, **kwargs: object) -> None:
        super().__init__(language=None, **kwargs)  # type: ignore[arg-type]
        self._history: list[str] = []
        self._history_index: int = -1
        self._draft: str = ""
        self._command_names: list[str] = []
        self._project_root: Path | None = None

    def set_completions(
        self,
        commands: list[str],
        project_root: Path | None = None,
    ) -> None:
        """Set available slash commands and project root for @ completions."""
        self._command_names = commands
        self._project_root = project_root

    def update_suggestion(self) -> None:
        """Called by Textual when text changes — provide inline completions."""
        text = self.text
        if not text:
            self.suggestion = ""
            return

        # Slash command completion: only when on first line with /prefix
        if text.startswith("/") and "\n" not in text:
            partial = text[1:]  # strip /
            for cmd in self._command_names:
                if cmd.startswith(partial) and cmd != partial:
                    self.suggestion = cmd[len(partial):]
                    return

        # @file completion: match the last @word
        last_at = text.rfind("@")
        if last_at >= 0:
            after_at = text[last_at + 1:]
            # Only complete if no space after the partial path
            if " " not in after_at and after_at and self._project_root:
                matches = self._fuzzy_file_match(after_at)
                if matches:
                    best = matches[0]
                    if best.startswith(after_at) and best != after_at:
                        self.suggestion = best[len(after_at):]
                        return

        self.suggestion = ""

    def _fuzzy_file_match(self, partial: str) -> list[str]:
        """Find files matching a partial path in the project root."""
        if not self._project_root:
            return []
        results: list[str] = []
        partial_lower = partial.lower()
        try:
            for path in self._project_root.rglob("*"):
                if not path.is_file():
                    continue
                rel = str(path.relative_to(self._project_root)).replace("\\", "/")
                if partial_lower in rel.lower():
                    results.append(rel)
                    if len(results) >= 10:
                        break
        except OSError:
            pass
        # Sort: exact prefix matches first, then contains
        results.sort(key=lambda r: (not r.lower().startswith(partial_lower), r))
        return results

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            # If there's a suggestion, accept it first instead of submitting
            if self.suggestion:
                self.insert(self.suggestion)
                self.suggestion = ""
                return
            text = self.text.strip()
            if text:
                self._history.append(text)
                self._history_index = -1
                self._draft = ""
                self.post_message(self.Submitted(text))
                self.clear()
        elif event.key == "tab":
            # Always intercept tab — never switch focus from input bar
            event.prevent_default()
            event.stop()
            if self.suggestion:
                self.insert(self.suggestion)
                self.suggestion = ""
        elif event.key == "up":
            if not self._history:
                return
            event.prevent_default()
            event.stop()
            if self._history_index == -1:
                self._draft = self.text
                self._history_index = len(self._history) - 1
            elif self._history_index > 0:
                self._history_index -= 1
            self.text = self._history[self._history_index]
            self.move_cursor_relative(columns=len(self.text))
        elif event.key == "down":
            if self._history_index == -1:
                return
            event.prevent_default()
            event.stop()
            if self._history_index < len(self._history) - 1:
                self._history_index += 1
                self.text = self._history[self._history_index]
            else:
                self._history_index = -1
                self.text = self._draft
            self.move_cursor_relative(columns=len(self.text))
        elif event.key == "shift+enter":
            # Allow newline insertion (default TextArea behavior)
            pass
