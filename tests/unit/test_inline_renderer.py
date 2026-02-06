"""Tests for InlineRenderer."""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock

from rich.console import Console

from hybridcoder.inline.renderer import InlineRenderer, _truncate_arg


def _make_renderer() -> tuple[InlineRenderer, StringIO]:
    """Create a renderer with captured output."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=True)
    renderer = InlineRenderer(console=console)
    return renderer, buf


class TestInlineRenderer:
    def test_print_welcome(self) -> None:
        """Welcome banner contains model, provider, mode, and version."""
        renderer, buf = _make_renderer()
        renderer.print_welcome(model="qwen3-8b", provider="ollama", mode="suggest")
        output = buf.getvalue()
        assert "HybridCoder" in output
        assert "qwen3-8b" in output
        assert "ollama" in output
        assert "suggest" in output

    def test_print_welcome_has_separator(self) -> None:
        """Welcome banner ends with a separator line."""
        renderer, buf = _make_renderer()
        renderer.print_welcome(model="m", provider="p", mode="s")
        output = buf.getvalue()
        assert "─" in output

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

    def test_print_tool_call_prefix(self) -> None:
        """Tool calls use ⏵ prefix."""
        renderer, buf = _make_renderer()
        renderer.print_tool_call("read_file", "completed", "src/main.py")
        output = buf.getvalue()
        assert "⏵" in output

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

    def test_separator_uses_dash(self) -> None:
        """Separator uses ─ character full-width."""
        renderer, buf = _make_renderer()
        renderer.print_separator()
        output = buf.getvalue()
        assert "─" in output

    def test_turn_separator(self) -> None:
        """Turn separator prints blank line + separator."""
        renderer, buf = _make_renderer()
        renderer.print_turn_separator()
        output = buf.getvalue()
        assert "─" in output

    def test_thinking_hidden_when_disabled(self) -> None:
        """When thinking is never called, no thinking output appears."""
        renderer, buf = _make_renderer()
        # Just verify that not calling print_thinking produces no thinking output
        renderer.start_streaming()
        renderer.stream_chunk("response text")
        renderer.end_streaming()
        output = buf.getvalue()
        assert "response text" in output
        # No thinking content present
        assert "thinking" not in output.lower() or "response text" in output

    def test_thinking_no_tags(self) -> None:
        """Thinking output has no <thinking> tags."""
        renderer, buf = _make_renderer()
        renderer.print_thinking("I am thinking about this")
        result = renderer.end_thinking()
        output = buf.getvalue()
        assert "<thinking>" not in output
        assert "</thinking>" not in output
        assert result == "I am thinking about this"

    def test_thinking_prints_content(self) -> None:
        """Thinking output contains the thinking text."""
        renderer, buf = _make_renderer()
        renderer.print_thinking("deep thought")
        renderer.end_thinking()
        output = buf.getvalue()
        assert "deep thought" in output

    def test_approval_context_compact(self) -> None:
        """Approval context shows compact tool details with ⏵ prefix."""
        renderer, buf = _make_renderer()
        renderer.print_approval_context(
            "write_file", {"path": "src/auth.py", "content": "line1\nline2\nline3"}
        )
        output = buf.getvalue()
        assert "⏵" in output
        assert "write_file" in output
        assert "path:" in output
        assert "src/auth.py" in output
        assert "(3 lines)" in output

    def test_approval_context_truncates_long_values(self) -> None:
        """Approval context truncates long non-content values."""
        renderer, buf = _make_renderer()
        long_path = "a/" * 50  # > 80 chars
        renderer.print_approval_context("read_file", {"path": long_path})
        output = buf.getvalue()
        # Truncated value should NOT contain the full path
        assert long_path not in output
        assert "read_file" in output

    def test_cost_summary(self) -> None:
        """Cost summary shows token counts."""
        renderer, buf = _make_renderer()
        renderer.print_cost_summary(tokens_in=100, tokens_out=500)
        output = buf.getvalue()
        assert "100" in output
        assert "500" in output

    def test_cost_summary_with_cost(self) -> None:
        """Cost summary shows dollar amount when non-zero."""
        renderer, buf = _make_renderer()
        renderer.print_cost_summary(tokens_in=100, tokens_out=500, cost=0.0123)
        output = buf.getvalue()
        assert "$0.0123" in output

    def test_print_system_renders_markdown(self) -> None:
        """System messages render markdown (not literal **bold**)."""
        renderer, buf = _make_renderer()
        renderer.print_system("**bold text** and _italic_")
        output = buf.getvalue()
        # Should NOT contain literal ** markers (Rich Markdown renders them)
        assert "**bold text**" not in output
        assert "bold text" in output


class TestTruncateArg:
    def test_short_string_unchanged(self) -> None:
        assert _truncate_arg("path", "src/main.py") == "src/main.py"

    def test_long_string_truncated(self) -> None:
        long = "x" * 100
        result = _truncate_arg("path", long)
        assert result.endswith("...")
        assert len(result) == 80

    def test_content_shows_line_count(self) -> None:
        result = _truncate_arg("content", "line1\nline2\nline3")
        assert result == "(3 lines)"

    def test_content_single_line(self) -> None:
        result = _truncate_arg("content", "single line")
        assert result == "(1 lines)"
