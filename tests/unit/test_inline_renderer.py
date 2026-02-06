"""Tests for InlineRenderer."""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock

from rich.console import Console

from hybridcoder.inline.renderer import InlineRenderer


def _make_renderer() -> tuple[InlineRenderer, StringIO]:
    """Create a renderer with captured output."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=True)
    renderer = InlineRenderer(console=console)
    return renderer, buf


class TestInlineRenderer:
    def test_print_welcome(self) -> None:
        """Welcome banner contains model, provider, and mode."""
        renderer, buf = _make_renderer()
        renderer.print_welcome(model="qwen3-8b", provider="ollama", mode="suggest")
        output = buf.getvalue()
        assert "HybridCoder" in output
        assert "qwen3-8b" in output
        assert "ollama" in output
        assert "suggest" in output

    def test_print_user_message(self) -> None:
        """User messages are printed with > prefix."""
        renderer, buf = _make_renderer()
        renderer.print_user_message("hello world")
        output = buf.getvalue()
        assert ">" in output
        assert "hello world" in output

    def test_print_assistant_message(self) -> None:
        """Assistant messages render as markdown."""
        renderer, buf = _make_renderer()
        renderer.print_assistant_message("# Hello\n\nThis is **bold**.")
        output = buf.getvalue()
        assert "Hello" in output

    def test_print_tool_call_success(self) -> None:
        """Successful tool calls show checkmark."""
        renderer, buf = _make_renderer()
        renderer.print_tool_call("read_file", "completed", "src/main.py")
        output = buf.getvalue()
        assert "read_file" in output
        assert "✓" in output

    def test_print_tool_call_error(self) -> None:
        """Failed tool calls show cross mark."""
        renderer, buf = _make_renderer()
        renderer.print_tool_call("run_command", "error", "Permission denied")
        output = buf.getvalue()
        assert "run_command" in output
        assert "✗" in output

    def test_print_diff(self) -> None:
        """Diffs show +/- markers."""
        renderer, buf = _make_renderer()
        renderer.print_diff("old line\n", "new line\n", "test.py")
        output = buf.getvalue()
        assert "test.py" in output

    def test_streaming_accumulates(self) -> None:
        """Streaming start/chunks/end returns concatenated content."""
        renderer, buf = _make_renderer()
        renderer.start_streaming()
        renderer.stream_chunk("Hello ")
        renderer.stream_chunk("world")
        result = renderer.end_streaming()
        assert result == "Hello world"

    def test_print_sessions_table(self) -> None:
        """Sessions table contains session data."""
        renderer, buf = _make_renderer()
        session = MagicMock()
        session.id = "abc12345-full-id"
        session.title = "Test Session"
        session.updated_at = None
        renderer.print_sessions_table([session])
        output = buf.getvalue()
        assert "abc12345" in output
        assert "Test Session" in output

    def test_input_border_top(self) -> None:
        """Top input border uses ╭ corner and ─ line."""
        renderer, buf = _make_renderer()
        renderer.print_input_border(top=True)
        output = buf.getvalue()
        assert "╭" in output
        assert "─" in output

    def test_input_border_bottom(self) -> None:
        """Bottom input border uses ╰ corner and ─ line."""
        renderer, buf = _make_renderer()
        renderer.print_input_border(top=False)
        output = buf.getvalue()
        assert "╰" in output
        assert "─" in output

    def test_input_borders_different_corners(self) -> None:
        """Top and bottom borders use different corner characters."""
        renderer, buf_top = _make_renderer()
        renderer.print_input_border(top=True)
        top_output = buf_top.getvalue()

        renderer2, buf_bot = _make_renderer()
        renderer2.print_input_border(top=False)
        bot_output = buf_bot.getvalue()

        assert "╭" in top_output and "╭" not in bot_output
        assert "╰" in bot_output and "╰" not in top_output

    def test_print_status_bar(self) -> None:
        """Status bar renders dim text with model/mode info."""
        renderer, buf = _make_renderer()
        renderer.print_status_bar("Model: test-model | Mode: suggest")
        output = buf.getvalue()
        assert "Model: test-model" in output
        assert "Mode: suggest" in output

    def test_print_status_bar_renders_dim(self) -> None:
        """Status bar text is rendered with dim styling."""
        renderer, buf = _make_renderer()
        renderer.print_status_bar("some info")
        output = buf.getvalue()
        assert "some info" in output
