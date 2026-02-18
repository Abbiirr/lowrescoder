"""Rich-based terminal output for inline mode.

Claude Code-style UX: main buffer, minimal chrome, full-width separators,
compact tool calls, streaming tokens, dim thinking.
"""

from __future__ import annotations

import difflib
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table


class InlineRenderer:
    """Rich-based terminal output for inline mode.

    Follows Claude Code visual language:
    - Full-width ─ separators between turns
    - Compact ⏵ tool call one-liners
    - Dim italic thinking (no <thinking> tags)
    - Minimal chrome, no borders
    """

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self._stream_buffer: list[str] = []
        self._streaming_active: bool = False
        self._thinking_buffer: list[str] = []

    # --- Startup/shutdown ---

    def print_welcome(self, model: str, provider: str, mode: str) -> None:
        """Print startup banner — clean info + separator, no ASCII art."""
        from autocode import __version__

        self.console.print(f"[bold]AutoCode[/bold] v{__version__}")
        self.console.print(f"[dim]Model: {model} | Provider: {provider} | Mode: {mode}[/dim]")
        self.console.print("[dim]Type /help for commands, Ctrl+D to exit[/dim]")
        self.print_separator()

    def print_goodbye(self) -> None:
        """Print exit message."""
        self.console.print("[dim]Goodbye.[/dim]")

    # --- Separators ---

    def print_separator(self) -> None:
        """Print full-width horizontal separator (Claude Code style)."""
        # Use CRLF to ensure prompt_toolkit prompts always start at column 0
        # across terminals/platforms (Windows newline handling can otherwise
        # leave the cursor at a non-zero column after a full-width line).
        # Printing exactly `console.width` characters can also trigger terminal
        # wrap edge cases; using width-1 is more robust while remaining
        # visually full-width.
        width = max(1, self.console.width - 1)
        self.console.print(f"[dim]{'─' * width}[/dim]", end="\r\n")

    def print_input_border(self, top: bool = True) -> None:
        """Print input area border.

        Top: ╭───
        Bottom: ╰───

        Note: No longer called from the REPL loop (borders removed to fix
        BUG-1/5/6). Kept for potential future use.
        """
        width = self.console.width
        border_char = "╭" if top else "╰"
        self.console.print(f"[dim]{border_char}{'─' * (width - 2)}[/dim]")

    def print_turn_separator(self) -> None:
        """Print separator between conversation turns."""
        self.print_separator()

    # --- Messages ---

    def print_user_message(self, text: str) -> None:
        """Print user message with > prefix."""
        self.console.print(f"[bold green]>[/bold green] {text}")
        self.console.print()

    def print_user_turn(self, text: str) -> None:
        """Print the user's submitted input as a turn in scrollback.

        Used when the prompt input itself is erased (`erase_when_done=True`) so
        streaming output doesn't look like it appears "inside" the input bar.
        """
        self.console.print(f"[bold green]❯[/bold green] {text}")

    def print_assistant_message(self, content: str) -> None:
        """Print completed assistant response as Rich Markdown."""
        self.console.print()
        self.console.print(Markdown(content))
        self.console.print()

    def print_system(self, message: str) -> None:
        """Print system message as Rich Markdown."""
        self.console.print(Markdown(message))

    # --- Tool calls ---

    def print_tool_call(self, tool_name: str, status: str, result: str = "") -> None:
        """Print compact tool call one-liner. Auto-ends thinking if active.

        Examples:
            ⏵ read_file src/main.py ✓
            ⏵ write_file src/auth.py ✓ (12 lines)
            ⏵ run_command ls ✗ Permission denied
        """
        if self._thinking_buffer:
            self.end_thinking()

        if status in ("completed", "success"):
            icon = "[green]✓[/green]"
        elif status in ("error", "blocked"):
            icon = "[red]✗[/red]"
        else:
            icon = "[yellow]…[/yellow]"

        line = f"[dim]⏵[/dim] {tool_name}"
        if result:
            line += f" [dim]{result[:100]}[/dim]"
        line += f" {icon}"
        self.console.print(line)

    # --- Thinking tokens ---

    def print_thinking(self, content: str) -> None:
        """Stream thinking tokens inline, dim italic. No <thinking> tags."""
        self._thinking_buffer.append(content)
        self.console.print(content, end="", highlight=False, style="dim italic")

    def end_thinking(self) -> str:
        """End thinking stream. Returns accumulated content."""
        content = "".join(self._thinking_buffer)
        if content:
            self.console.print()  # End the last thinking line
            self.console.print()  # Blank line before response
        self._thinking_buffer = []
        return content

    # --- Diffs ---

    def print_diff(self, old_content: str, new_content: str, file_path: str) -> None:
        """Print unified diff with syntax highlighting."""
        diff_lines = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        )
        diff_text = "".join(diff_lines)
        if diff_text:
            self.console.print(Syntax(diff_text, "diff", theme="monokai"))
        else:
            self.console.print("[dim]No changes.[/dim]")

    # --- Approval context ---

    def print_approval_context(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Print compact tool details before showing approval prompt.

        Example:
            ⏵ write_file
              path: src/auth.py
              content: (47 lines)
        """
        self.console.print(f"[dim]⏵[/dim] [bold]{tool_name}[/bold]")
        for key, value in arguments.items():
            display_value = _truncate_arg(key, value)
            self.console.print(f"  [dim]{key}:[/dim] {display_value}", highlight=False)

    # --- Sessions table ---

    def print_sessions_table(self, sessions: list[Any]) -> None:
        """Print sessions list as Rich Table."""
        table = Table(title="Sessions")
        table.add_column("#", style="dim")
        table.add_column("ID", style="cyan")
        table.add_column("Title")
        table.add_column("Updated")
        for i, s in enumerate(sessions, 1):
            title = s.title or "(untitled)"
            if len(title) > 40:
                title = title[:37] + "..."
            table.add_row(
                str(i),
                s.id[:8],
                title,
                s.updated_at.strftime("%Y-%m-%d %H:%M") if s.updated_at else "",
            )
        self.console.print(table)

    # --- Status bar ---

    def print_status_bar(self, text: str) -> None:
        """Print status info line (dim text)."""
        self.console.print(f"[dim] {text}[/dim]")

    # --- Cost summary ---

    def print_cost_summary(
        self,
        tokens_in: int,
        tokens_out: int,
        cost: float = 0.0,
    ) -> None:
        """Print per-turn cost line (dim, inline)."""
        parts = [f"Tokens: {tokens_in}→{tokens_out}"]
        if cost > 0:
            parts.append(f"Cost: ${cost:.4f}")
        self.console.print(f"[dim]{' | '.join(parts)}[/dim]", highlight=False)

    # --- Streaming ---

    def start_streaming(self) -> None:
        """Begin streaming mode. Call stream_chunk() for each token."""
        self._stream_buffer = []
        self._streaming_active = True

    def stream_chunk(self, chunk: str) -> None:
        """Print a streaming chunk. Auto-ends thinking if active."""
        if self._thinking_buffer:
            self.end_thinking()
        self._stream_buffer.append(chunk)
        self.console.print(chunk, end="", highlight=False)

    def end_streaming(self) -> str:
        """End streaming. Returns full accumulated content."""
        if not self._streaming_active:
            return ""
        content = "".join(self._stream_buffer)
        # End the streaming line; spacing after a turn is handled by
        # print_turn_separator() in the REPL loop.
        self.console.print(end="\r\n")
        self._stream_buffer = []
        self._streaming_active = False
        return content

    # --- Thinking indicator ---

    def print_thinking_indicator(self) -> None:
        """Print a static thinking indicator before LLM response."""
        self.console.print("[dim italic]Thinking...[/dim italic]")


def _truncate_arg(key: str, value: Any) -> str:
    """Truncate argument values for compact display."""
    s = str(value)
    if key == "content" and isinstance(value, str):
        line_count = value.count("\n") + 1
        return f"({line_count} lines)"
    if len(s) > 80:
        return s[:77] + "..."
    return s
