"""Interactive approval prompts and option selection widgets.

Uses Textual's built-in OptionList for arrow-key navigation.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import OptionList, Static

logger = logging.getLogger(__name__)


class ApprovalPrompt(Vertical):
    """Interactive approval prompt for tool call approval.

    Mount in chat, focus, and await the future to get the user's response.
    The future resolves to (response, always) where response is "yes" or "no"
    and always indicates if the user chose "always allow".

    Uses arrow keys + Enter for selection.
    """

    DEFAULT_CSS = """
    ApprovalPrompt {
        margin: 1 0;
        padding: 1 2;
        background: $surface;
        border: tall $warning;
        height: auto;
        max-height: 10;
    }
    ApprovalPrompt OptionList {
        height: auto;
        max-height: 5;
    }
    """

    def __init__(
        self,
        tool_name: str,
        description: str,
        future: asyncio.Future[tuple[str, bool]],
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._tool_name = tool_name
        self._description = description
        self._future = future

    def compose(self) -> ComposeResult:
        yield Static(
            f"[bold yellow]Allow {self._tool_name}?[/]\n"
            f"  {self._description}",
        )
        yield OptionList(
            "Yes",
            "No",
            "Always allow",
            id="approval-choices",
        )

    def on_mount(self) -> None:
        self.call_after_refresh(self._focus_options)

    def _focus_options(self) -> None:
        option_list = self.query_one("#approval-choices", OptionList)
        option_list.focus()

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected,
    ) -> None:
        logger.debug("ApprovalPrompt: option selected idx=%d", event.option_index)
        if self._future.done():
            return
        idx = event.option_index
        if idx == 0:  # Yes
            self._future.set_result(("yes", False))
        elif idx == 1:  # No
            self._future.set_result(("no", False))
        elif idx == 2:  # Always allow
            self._future.set_result(("yes", True))

    def on_key(self, event: Any) -> None:
        """Handle escape to cancel."""
        key = getattr(event, "key", None)
        logger.debug("ApprovalPrompt.on_key: %s", key)
        if key == "escape":
            if not self._future.done():
                self._future.set_result(("no", False))


class OptionSelector(Vertical):
    """Arrow-key navigable option selection widget.

    Mount in chat, focus, and await the future to get selected options.
    Single-select: arrow keys + Enter to choose.
    Multi-select: arrow keys + Space to toggle, Enter to confirm.
    Escape cancels (returns empty list).
    """

    DEFAULT_CSS = """
    OptionSelector {
        margin: 1 0;
        padding: 1 2;
        background: $surface;
        border: tall $accent;
        height: auto;
        max-height: 15;
    }
    OptionSelector OptionList {
        height: auto;
        max-height: 10;
    }
    """

    def __init__(
        self,
        prompt: str,
        options: list[str],
        future: asyncio.Future[list[str]],
        *,
        multi: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._options = options
        self._multi = multi
        self._selected: set[int] = set()
        self._prompt_text = prompt
        self._future = future

    def compose(self) -> ComposeResult:
        hint = "Enter to toggle, select Done when finished" if self._multi else "Enter to select"
        yield Static(f"[bold]{self._prompt_text}[/]\n  [dim]{hint}[/]")
        option_labels = []
        for opt in self._options:
            if self._multi:
                option_labels.append(f"[ ] {opt}")
            else:
                option_labels.append(opt)
        if self._multi:
            option_labels.append("[bold green]Done[/]")
        yield OptionList(*option_labels, id="option-choices")

    def on_mount(self) -> None:
        self.call_after_refresh(self._focus_options)

    def _focus_options(self) -> None:
        option_list = self.query_one("#option-choices", OptionList)
        option_list.focus()

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected,
    ) -> None:
        logger.debug("OptionSelector: option selected idx=%d", event.option_index)
        if self._future.done():
            return
        idx = event.option_index
        if self._multi:
            # "Done" is the last option
            if idx == len(self._options):
                choices = [self._options[i] for i in sorted(self._selected)]
                logger.debug("OptionSelector: Done selected, choices=%s", choices)
                self._future.set_result(choices)
                return
            # Toggle selection
            self._selected ^= {idx}
            check = "[x]" if idx in self._selected else "[ ]"
            option_list = self.query_one("#option-choices", OptionList)
            option_list.replace_option_prompt_at_index(
                idx, f"{check} {self._options[idx]}",
            )
        else:
            # Single-select: resolve immediately
            logger.debug("OptionSelector: single-select %s", self._options[idx])
            self._future.set_result([self._options[idx]])

    def on_key(self, event: Any) -> None:
        """Handle escape to cancel."""
        key = getattr(event, "key", None)
        logger.debug("OptionSelector.on_key: %s", key)
        if key == "escape":
            if not self._future.done():
                self._future.set_result([])
