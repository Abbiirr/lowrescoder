"""Scrollable chat view widget for displaying messages."""

from __future__ import annotations

from typing import Any

from textual.containers import VerticalScroll
from textual.widgets import Collapsible, Markdown, Static


class ChatView(VerticalScroll):
    """Scrollable container that displays chat messages."""

    DEFAULT_CSS = """
    ChatView {
        height: 1fr;
        padding: 0 1;
    }
    ChatView .user-message {
        color: $text;
        margin: 1 0 0 4;
    }
    ChatView .assistant-message {
        margin: 0 0 1 0;
    }
    ChatView .system-message {
        color: $text-muted;
        text-style: italic;
        margin: 1 0;
    }
    ChatView .thinking-indicator {
        color: $accent;
        text-style: italic;
        margin: 0 0;
    }
    ChatView Collapsible {
        margin: 0 0;
        padding: 0;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._streaming_widget: Static | None = None
        self._streaming_content: str = ""
        self._thinking_widget: Static | None = None
        self._thinking_stream_widget: Static | None = None
        self._thinking_stream_content: str = ""
        self._frozen: bool = False

    @property
    def frozen(self) -> bool:
        """Whether auto-scroll is frozen (for text selection)."""
        return self._frozen

    def freeze(self) -> None:
        """Pause auto-scroll so the user can select text with the mouse."""
        self._frozen = True

    def unfreeze(self) -> None:
        """Resume auto-scroll and jump to bottom."""
        self._frozen = False
        self.scroll_end(animate=False)

    def _auto_scroll(self) -> None:
        """Scroll to bottom unless frozen."""
        if not self._frozen:
            self.scroll_end(animate=False)

    def add_message(self, role: str, content: str) -> None:
        """Add a complete message to the chat."""
        if role == "user":
            self.mount(Static(
                f"[bold green]> [/]{content}", classes="user-message",
            ))
        elif role == "assistant":
            self.mount(Markdown(content, classes="assistant-message"))
        else:
            self.mount(Static(
                f"[dim]{content}[/]", classes="system-message",
            ))
        self._auto_scroll()

    def add_tool_call_display(self, tool_name: str, status: str, result: str = "") -> None:
        """Display a tool call in the chat."""
        icon = "\u2713" if status == "completed" else "\u2717" if status == "error" else "\u25cb"
        text = f"[dim]{icon} {tool_name}[/]"
        if result:
            text += f"\n[dim]{result[:200]}[/]"
        widget = Static(text, classes="system-message")
        self.mount(widget)
        self._auto_scroll()

    def show_thinking(self) -> None:
        """Show a thinking indicator in the chat."""
        if self._thinking_widget is None:
            self._thinking_widget = Static(
                "[dim italic]Thinking...[/]", classes="thinking-indicator",
            )
            self.mount(self._thinking_widget)
            self._auto_scroll()

    def hide_thinking(self) -> None:
        """Remove the thinking indicator."""
        if self._thinking_widget is not None:
            self._thinking_widget.remove()
            self._thinking_widget = None

    def add_thinking_chunk(self, chunk: str) -> None:
        """Append a thinking/reasoning chunk to the thinking display."""
        self._thinking_stream_content += chunk
        if self._thinking_stream_widget is None:
            self._thinking_stream_widget = Static(
                f"[dim italic]{self._thinking_stream_content}[/]",
                classes="thinking-indicator",
            )
            self.mount(self._thinking_stream_widget)
        else:
            self._thinking_stream_widget.update(
                f"[dim italic]{self._thinking_stream_content}[/]"
            )
        self._auto_scroll()

    def finish_thinking_stream(self) -> str:
        """Finalize the thinking stream.

        Replaces the live Static with a Collapsible widget containing the
        final thinking content (collapsed by default). Returns the content.
        """
        content = self._thinking_stream_content
        if self._thinking_stream_widget is not None:
            self._thinking_stream_widget.remove()
            self._thinking_stream_widget = None
        self._thinking_stream_content = ""
        if content:
            try:
                collapsible = Collapsible(
                    Static(f"[dim italic]{content}[/]"),
                    title="Thinking",
                    collapsed=True,
                )
                self.mount(collapsible)
                self._auto_scroll()
            except Exception:
                pass  # Widget not mounted in an app, skip collapsible
        return content

    def start_streaming(self) -> None:
        """Begin streaming a new assistant response.

        Uses a lightweight Static widget during streaming to avoid
        expensive Markdown re-parsing on every chunk.  The Static is
        swapped for a proper Markdown widget in finish_streaming().
        """
        self.hide_thinking()
        self._streaming_content = ""
        self._streaming_widget = Static("", classes="assistant-message")
        self.mount(self._streaming_widget)

    def add_streaming_chunk(self, chunk: str) -> None:
        """Append a chunk to the current streaming response."""
        self._streaming_content += chunk
        if self._streaming_widget is not None:
            self._streaming_widget.update(self._streaming_content)
            self._auto_scroll()

    def finish_streaming(self) -> str:
        """Finish streaming and swap the Static for a Markdown widget."""
        self.hide_thinking()
        content = self._streaming_content
        # Replace the lightweight Static with a properly rendered Markdown
        if self._streaming_widget is not None:
            self._streaming_widget.remove()
            self.mount(Markdown(content, classes="assistant-message"))
            self._auto_scroll()
        self._streaming_widget = None
        self._streaming_content = ""
        return content
