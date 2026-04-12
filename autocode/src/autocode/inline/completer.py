"""prompt_toolkit completer and auto-suggest for / commands and @ file paths."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from prompt_toolkit.auto_suggest import AutoSuggest, Suggestion
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from autocode.tui.commands import CommandRouter
from autocode.tui.file_completer import fuzzy_complete


class HybridAutoSuggest(AutoSuggest):
    """Auto-suggest ghost text for slash commands and @file paths.

    Shows grayed-out completion after the cursor as the user types.
    Example: user types "/res" → ghost text "ume" appears dimmed.
    Example: user types "@src/hy" → ghost text "bridcoder/..." appears dimmed.
    """

    def __init__(self, command_router: CommandRouter, project_root: Path | None = None) -> None:
        self.command_router = command_router
        self.project_root = project_root or Path.cwd()

    def get_suggestion(
        self, buffer: Buffer, document: Document,
    ) -> Suggestion | None:
        text = document.text_before_cursor

        # Slash command ghost text: /res → ume (grayed out)
        if text.startswith("/") and len(text) > 1:
            partial = text[1:]
            for cmd in self.command_router.get_all():
                if cmd.name.startswith(partial) and cmd.name != partial:
                    return Suggestion(cmd.name[len(partial):])
                for alias in cmd.aliases:
                    if alias.startswith(partial) and alias != partial:
                        return Suggestion(alias[len(partial):])

        # @file ghost text: @src/hy → bridcoder/... (grayed out)
        if "@" in text:
            at_pos = text.rfind("@")
            partial = text[at_pos + 1:]
            if partial:
                matches = fuzzy_complete(partial, self.project_root)
                if matches and matches[0].lower().startswith(partial.lower()):
                    return Suggestion(matches[0][len(partial):])

        return None


class HybridCompleter(Completer):
    """prompt_toolkit completer for / commands and @ file paths."""

    def __init__(self, command_router: CommandRouter, project_root: Path) -> None:
        self.command_router = command_router
        self.project_root = project_root

    def get_completions(
        self, document: Document, complete_event: object
    ) -> Iterable[Completion]:
        text = document.text_before_cursor

        # Slash command completion: /he → /help, /hel → /help
        if text.startswith("/"):
            partial = text[1:]  # Remove leading /
            for cmd in self.command_router.get_all():
                if cmd.name.startswith(partial):
                    yield Completion(
                        cmd.name,
                        start_position=-len(partial),
                        display_meta=cmd.description,
                    )
                for alias in cmd.aliases:
                    if alias.startswith(partial):
                        yield Completion(
                            alias,
                            start_position=-len(partial),
                            display_meta=f"→ /{cmd.name}",
                        )

        # @file completion: @src/au → @src/autocode/...
        elif "@" in text:
            at_pos = text.rfind("@")
            partial = text[at_pos + 1:]
            if partial:  # Don't complete bare @
                matches = fuzzy_complete(partial, self.project_root, max_results=10)
                for match in matches:
                    yield Completion(
                        match,
                        start_position=-len(partial),
                        display_meta="file",
                    )
