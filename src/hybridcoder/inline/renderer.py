"""Rich-based terminal output for inline mode."""

from __future__ import annotations

import difflib
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table


class InlineRenderer:
    """Rich-based terminal output for inline mode."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self._stream_buffer: list[str] = []
        self._thinking_buffer: list[str] = []

    # --- Startup/shutdown ---

    def print_welcome(self, model: str, provider: str, mode: str) -> None:
        """Print startup banner with model, provider, approval mode."""
        self.console.print(
            f"[bold]HybridCoder[/bold] | Model: {model} | Provider: {provider} | Mode: {mode}"
        )
        self.console.print("[dim]Type /help for commands, Ctrl+D to exit[/dim]")
        self.console.print()

    def print_goodbye(self) -> None:
        """Print exit message."""
        self.console.print("[dim]Goodbye.[/dim]")

    # --- Messages ---

    def print_user_message(self, text: str) -> None:
        """Print user message with "> " prefix."""
        self.console.print(f"[bold green]>[/bold green] {text}")
        self.console.print()

    def print_assistant_message(self, content: str) -> None:
        """Print completed assistant response as Rich Markdown."""
        self.console.print(Markdown(content))
        self.console.print()

    def print_system(self, message: str) -> None:
        """Print system message (command output, errors, info).

        Renders as Markdown since command handlers produce Markdown-formatted
        output (bold, italic, code, lists).
        """
        self.console.print(Markdown(message))

    # --- Tool calls ---

    def print_tool_call(self, tool_name: str, status: str, result: str = "") -> None:
        """Print tool call status line. Auto-ends thinking if active.

        Examples:
            [tool] read_file: src/main.py ✓
            [tool] run_command ✗ Permission denied
        """
        if self._thinking_buffer:
            self.end_thinking()

        if status in ("completed", "success"):
            icon = "[green]✓[/green]"
        elif status in ("error", "blocked"):
            icon = "[red]✗[/red]"
        else:
            icon = "[yellow]…[/yellow]"

        line = f"[dim]\\[tool][/dim] {tool_name} {icon}"
        if result:
            line += f" [dim]{result[:100]}[/dim]"
        self.console.print(line)

    # --- Thinking tokens ---

    def print_thinking(self, content: str) -> None:
        """Stream thinking tokens inline, dim styled."""
        if not self._thinking_buffer:
            # First thinking chunk — print a dim prefix
            self.console.print("[dim italic]<thinking>[/dim italic]", highlight=False)
        self._thinking_buffer.append(content)
        self.console.print(content, end="", highlight=False, style="dim")

    def end_thinking(self) -> str:
        """End thinking stream with separator. Returns accumulated content."""
        content = "".join(self._thinking_buffer)
        if content:
            self.console.print()  # End the last thinking line
            self.console.print("[dim italic]</thinking>[/dim italic]", highlight=False)
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
        """Print tool details before showing approval prompt."""
        import json

        self.console.print(f"[bold yellow]Tool:[/bold yellow] {tool_name}")
        self.console.print(f"[dim]{json.dumps(arguments, indent=2)}[/dim]")

    # --- Sessions table ---

    def print_sessions_table(self, sessions: list[Any]) -> None:
        """Print sessions list as Rich Table."""
        table = Table(title="Sessions")
        table.add_column("#", style="dim")
        table.add_column("ID", style="cyan")
        table.add_column("Title")
        table.add_column("Updated")
        for i, s in enumerate(sessions, 1):
            table.add_row(
                str(i),
                s.id[:8],
                s.title or "(untitled)",
                s.updated_at.strftime("%Y-%m-%d %H:%M") if s.updated_at else "",
            )
        self.console.print(table)

    # --- Status bar ---

    def print_status_bar(self, text: str) -> None:
        """Print status info line above the input box."""
        self.console.print(f"[dim] {text}[/dim]")

    # --- Input box ---

    def print_input_border(self, *, top: bool = True) -> None:
        """Print input box border (top or bottom).

        Creates a Claude Code-style framed input area:
            ╭─────────────────────────
            │ ❯ user types here
            ╰─────────────────────────
        """
        width = min(self.console.width, 120)
        corner = "╭" if top else "╰"
        self.console.print(f"[dim]{corner}{'─' * (width - 1)}[/dim]")

    # --- Streaming ---

    def start_streaming(self) -> None:
        """Begin streaming mode. Call stream_chunk() for each token."""
        self._stream_buffer = []

    def stream_chunk(self, chunk: str) -> None:
        """Print a streaming chunk. Auto-ends thinking if active."""
        if self._thinking_buffer:
            self.end_thinking()
        self._stream_buffer.append(chunk)
        self.console.print(chunk, end="", highlight=False)

    def end_streaming(self) -> str:
        """End streaming. Returns full accumulated content."""
        content = "".join(self._stream_buffer)
        self.console.print()  # Final newline
        self.console.print()  # Blank line separator
        self._stream_buffer = []
        return content
