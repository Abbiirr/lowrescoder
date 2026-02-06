"""Inline REPL using Rich + prompt_toolkit.

Claude Code-style sequential REPL: output streams above, prompt appears after.
Bottom toolbar shows model/mode/tokens/edits. Thinking hidden by default.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console

from hybridcoder.agent.approval import ApprovalManager, ApprovalMode
from hybridcoder.agent.loop import AgentLoop
from hybridcoder.agent.tools import ToolRegistry, create_default_registry
from hybridcoder.config import HybridCoderConfig, load_config
from hybridcoder.inline.completer import HybridAutoSuggest, HybridCompleter
from hybridcoder.inline.renderer import InlineRenderer
from hybridcoder.layer4.llm import create_provider
from hybridcoder.session.store import SessionStore
from hybridcoder.tui.commands import CommandRouter, create_default_router
from hybridcoder.tui.file_completer import expand_references


class InlineApp:
    """Inline REPL using Rich + prompt_toolkit.

    This is the canonical rendering mode for HybridCoder.
    Output goes to stdout (becomes terminal scrollback).
    Input handled by prompt_toolkit (async readline with completion).

    Sequential model: prompt -> process -> output -> prompt.
    No concurrent streaming+input (deferred to Phase 5).
    """

    def __init__(
        self,
        config: HybridCoderConfig | None = None,
        session_id: str | None = None,
        project_root: Path | None = None,
    ) -> None:
        self.config = config or load_config()
        self.project_root = project_root or Path.cwd()

        # Output
        self.console = Console()
        self.renderer = InlineRenderer(self.console)

        # Session
        db_path = Path(self.config.tui.session_db_path).expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_store = SessionStore(str(db_path))

        if session_id:
            self.session_id = session_id
        else:
            self.session_id = self.session_store.create_session(
                title="New session",
                model=self.config.llm.model,
                provider=self.config.llm.provider,
                project_dir=str(self.project_root),
            )

        # Commands
        self.command_router: CommandRouter = create_default_router()

        # Input (prompt_toolkit) — lazy init in run() to avoid terminal detection in tests
        self.completer = HybridCompleter(self.command_router, self.project_root)
        self.auto_suggest = HybridAutoSuggest(self.command_router)
        self.session: PromptSession[str] | None = None

        # Agent (lazy init)
        self._provider: Any = None
        self._tool_registry: ToolRegistry | None = None
        self._approval_manager: ApprovalManager | None = None
        self._agent_loop: AgentLoop | None = None
        self._session_titled: bool = False
        self._interrupt_count: int = 0

        # Thinking visibility (hidden by default, matching Claude Code)
        self._show_thinking: bool = False

        # Session-level auto-approve tracking
        self._session_approved_tools: set[str] = set()

        # Stats tracking
        self._total_tokens: int = 0
        self._edit_count: int = 0
        self._files_modified: set[str] = set()

    # --- AppContext protocol methods ---

    def add_system_message(self, content: str) -> None:
        """Print a system message via renderer."""
        self.renderer.print_system(content)

    def clear_messages(self) -> None:
        """Clear indicator for inline mode (no widget to clear)."""
        self.console.print("[dim]--- (cleared) ---[/dim]")

    def display_messages(self, messages: list[Any]) -> None:
        """Re-display messages from session history."""
        for msg in messages:
            if msg.role == "user":
                self.renderer.print_user_message(msg.content)
            elif msg.role == "assistant":
                self.renderer.print_assistant_message(msg.content)
            else:
                self.renderer.print_system(msg.content)

    def get_assistant_messages(self) -> list[str]:
        """Get assistant messages from session store."""
        messages = self.session_store.get_messages(self.session_id)
        return [m.content for m in messages if m.role == "assistant"]

    def copy_to_clipboard(self, text: str) -> bool:
        """Copy text to system clipboard."""
        from hybridcoder.tui.commands import _copy_to_clipboard

        return _copy_to_clipboard(text)

    def exit_app(self) -> None:
        """Exit the REPL by raising EOFError."""
        raise EOFError

    @property
    def approval_mode(self) -> str:
        if self._approval_manager:
            return self._approval_manager.mode.value
        return self.config.tui.approval_mode

    @approval_mode.setter
    def approval_mode(self, value: str) -> None:
        self.config.tui.approval_mode = value  # type: ignore[assignment]
        mode = ApprovalMode(value)
        if self._approval_manager:
            self._approval_manager.mode = mode

    @property
    def shell_enabled(self) -> bool:
        return self.config.shell.enabled

    @shell_enabled.setter
    def shell_enabled(self, value: bool) -> None:
        self.config.shell.enabled = value
        if self._approval_manager:
            self._approval_manager.shell_config.enabled = value

    @property
    def show_thinking(self) -> bool:
        """Whether thinking tokens are visible."""
        return self._show_thinking

    @show_thinking.setter
    def show_thinking(self, value: bool) -> None:
        self._show_thinking = value

    # --- Lifecycle ---

    def _get_status_text(self) -> str:
        """Return status info string for the bottom toolbar."""
        model = self.config.llm.model
        mode = self.approval_mode
        parts = [f"Model: {model}", f"Mode: {mode}"]

        if self._total_tokens > 0:
            if self._total_tokens >= 1000:
                token_str = f"~{self._total_tokens / 1000:.1f}k"
            else:
                token_str = f"~{self._total_tokens}"
            parts.append(f"Tokens: {token_str}")

        if self._edit_count > 0:
            parts.append(f"Edits: {self._edit_count}")

        if self._files_modified:
            parts.append(f"Files: {len(self._files_modified)}")

        return " | ".join(parts)

    def _create_key_bindings(self) -> KeyBindings:
        """Create custom key bindings for the REPL."""
        kb = KeyBindings()

        @kb.add("s-tab")
        def _cycle_mode(event: Any) -> None:
            """Shift+Tab cycles approval modes."""
            modes = ["read-only", "suggest", "auto"]
            current = self.approval_mode
            idx = modes.index(current) if current in modes else 0
            self.approval_mode = modes[(idx + 1) % len(modes)]
            # Invalidate toolbar to show new mode
            event.app.invalidate()

        return kb

    def _ensure_prompt_session(self) -> PromptSession[str]:
        """Create PromptSession lazily (avoids terminal detection during tests)."""
        if self.session is None:
            history_path = Path("~/.hybridcoder/history").expanduser()
            history_path.parent.mkdir(parents=True, exist_ok=True)
            self.session = PromptSession(
                history=FileHistory(str(history_path)),
                completer=self.completer,
                auto_suggest=self.auto_suggest,
                multiline=False,
                complete_while_typing=False,
                bottom_toolbar=self._get_status_text,
                key_bindings=self._create_key_bindings(),
            )
        return self.session

    async def run(self) -> None:
        """Main REPL loop. Blocks until /exit or Ctrl+D.

        Flow:
            Welcome banner + separator
            Loop:
              ❯ [user types]
              [streaming response...]
              [tool] read_file ✓
              [formatted response]
              ─────────────────────
              ❯ [next prompt]
        """
        prompt_session = self._ensure_prompt_session()
        self.renderer.print_welcome(
            model=self.config.llm.model,
            provider=self.config.llm.provider,
            mode=self.config.tui.approval_mode,
        )

        input_prompt = FormattedText(
            [
                ("fg:ansigreen bold", "❯ "),
            ]
        )

        while True:
            try:
                text = await prompt_session.prompt_async(input_prompt)

                if not text.strip():
                    continue
                self._interrupt_count = 0
                await self._handle_input_with_cancel(text.strip())
                # Separator AFTER response, before next prompt
                self.renderer.print_turn_separator()
            except EOFError:
                break
            except KeyboardInterrupt:
                if self._agent_loop:
                    self._agent_loop.cancel()
                    self.console.print("[dim]^C — generation cancelled[/dim]")
                else:
                    self.console.print(
                        "[dim]^C — Press Ctrl+C again to quit, or Ctrl+D[/dim]",
                    )
                    self._interrupt_count += 1
                    if self._interrupt_count >= 2:
                        break
                    continue
                self._interrupt_count = 0
                continue

        self.renderer.print_goodbye()

    async def _handle_input_with_cancel(self, text: str) -> None:
        """Wrap _handle_input in a cancellable task with Escape listener."""
        # Slash commands don't need cancellation
        if text.startswith("/"):
            await self._handle_input(text)
            return

        agent_task = asyncio.create_task(self._handle_input(text))
        escape_task = asyncio.create_task(self._listen_for_escape())

        done, pending = await asyncio.wait(
            [agent_task, escape_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        if escape_task in done:
            try:
                escaped = escape_task.result()
            except asyncio.CancelledError:
                escaped = False
            if escaped:
                if self._agent_loop:
                    self._agent_loop.cancel()
                self.renderer.end_thinking()
                self.renderer.end_streaming()
                self.console.print("\n[dim]Cancelled.[/dim]")
                return

        # Re-raise any agent_task exception
        if agent_task in done:
            agent_task.result()  # raises if failed

    def _poll_key_windows(self) -> str | None:
        """Check for keypress on Windows. Returns key byte or None."""
        import msvcrt

        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key in (b"\x1b", b"\x03"):
                return key.decode("latin-1")
        return None

    def _poll_key_unix(self, fd: int) -> str | None:
        """Check for keypress on Unix. Returns char or None."""
        import select
        import sys

        ready, _, _ = select.select([fd], [], [], 0.05)
        if ready:
            ch = sys.stdin.read(1)
            if ch in ("\x1b", "\x03"):
                return ch
        return None

    async def _listen_for_escape(self) -> bool:
        """Listen for Escape key press. Returns True if pressed."""
        import sys

        loop = asyncio.get_running_loop()

        if sys.platform == "win32":
            while True:
                key = await loop.run_in_executor(None, self._poll_key_windows)
                if key is not None:
                    return True
                await asyncio.sleep(0.05)
        else:
            import termios
            import tty

            fd = sys.stdin.fileno()
            try:
                old_settings = termios.tcgetattr(fd)
            except termios.error:
                return False  # Not a TTY — can't listen for keys
            try:
                tty.setraw(fd)
                while True:
                    key = await loop.run_in_executor(
                        None, self._poll_key_unix, fd,
                    )
                    if key is not None:
                        return True
                    await asyncio.sleep(0.05)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    async def _handle_input(self, text: str) -> None:
        """Route input to slash command or agent loop."""
        # Try slash command first
        result = self.command_router.dispatch(text)
        if result is not None:
            cmd, args = result
            await cmd.handler(self, args)
            return

        # Expand @file references
        expanded = expand_references(text, self.project_root)

        # Run agent
        await self._run_agent(expanded)

    # --- Agent ---

    def _ensure_agent_loop(self) -> AgentLoop:
        """Lazy-initialize agent loop with all dependencies."""
        if self._agent_loop is None:
            self._provider = create_provider(self.config)
            self._tool_registry = create_default_registry(
                project_root=str(self.project_root),
            )
            self._approval_manager = ApprovalManager(
                mode=ApprovalMode(self.config.tui.approval_mode),
                shell_config=self.config.shell,
            )

            # Load project memory if available
            memory_path = self.project_root / ".hybridcoder" / "memory.md"
            memory_content = None
            if memory_path.exists():
                try:
                    memory_content = memory_path.read_text(encoding="utf-8")
                except OSError:
                    pass

            self._agent_loop = AgentLoop(
                provider=self._provider,
                tool_registry=self._tool_registry,
                approval_manager=self._approval_manager,
                session_store=self.session_store,
                session_id=self.session_id,
                memory_content=memory_content,
            )

        return self._agent_loop

    def _on_tool_call(self, tool_name: str, status: str, result: str = "") -> None:
        """Track tool stats and forward to renderer."""
        self.renderer.print_tool_call(tool_name, status, result)

        # Track edits and files modified
        if status in ("completed", "success") and tool_name == "write_file":
            self._edit_count += 1
            # Extract file path from result (first arg is usually the path)
            if result:
                self._files_modified.add(result.split("\n")[0][:200])

    async def _run_agent(self, user_message: str) -> None:
        """Run agent loop and stream output via renderer."""
        # Don't reprint user message — prompt_toolkit already displayed it.
        self.console.print()  # Blank line after user input
        self.renderer.print_thinking_indicator()

        # Auto-title session from first user message
        if not self._session_titled:
            title = user_message[:60] + ("..." if len(user_message) > 60 else "")
            self.session_store.update_session(self.session_id, title=title)
            self._session_titled = True

        agent_loop = self._ensure_agent_loop()
        # Update session ID in case it changed (e.g. /new was used)
        agent_loop.session_id = self.session_id

        # Start streaming
        self.renderer.start_streaming()

        # Conditionally pass thinking callback based on _show_thinking
        on_thinking = self.renderer.print_thinking if self._show_thinking else None

        try:
            await agent_loop.run(
                user_message,
                on_chunk=self.renderer.stream_chunk,
                on_thinking_chunk=on_thinking,
                on_tool_call=self._on_tool_call,
                approval_callback=self._approval_prompt,
                ask_user_callback=self._ask_user_prompt,
            )
        except asyncio.CancelledError:
            self.renderer.end_thinking()
            self.renderer.end_streaming()
            self.renderer.print_system("[Cancelled]")
            return
        except Exception as e:
            self.renderer.end_thinking()
            self.renderer.end_streaming()
            self.renderer.print_system(f"Error: {e}")
            return

        self.renderer.end_thinking()
        content = self.renderer.end_streaming()

        # Approximate token count from streamed content (1 token ~= 4 chars)
        if content:
            self._total_tokens += max(1, len(content) // 4)
        # Count user input tokens too
        self._total_tokens += max(1, len(user_message) // 4)

    # --- Interactive prompts ---

    async def _arrow_select(
        self,
        title: str,
        options: list[str],
        default_index: int = 0,
    ) -> str | None:
        """Arrow-key selector for options. Returns selected value or None on cancel.

        Renders an inline list with ❯ marker that moves with Up/Down arrows.
        Enter accepts, Escape cancels.
        """
        from prompt_toolkit.application import Application
        from prompt_toolkit.key_binding import KeyBindings as SelectKB
        from prompt_toolkit.layout import Layout
        from prompt_toolkit.layout.containers import Window
        from prompt_toolkit.layout.controls import FormattedTextControl
        from prompt_toolkit.styles import Style

        selected = [default_index]

        def get_text() -> list[tuple[str, str]]:
            result: list[tuple[str, str]] = []
            for i, opt in enumerate(options):
                if i == selected[0]:
                    result.append(("class:highlight", f"  ❯ {opt}"))
                else:
                    result.append(("class:option", f"    {opt}"))
                if i < len(options) - 1:
                    result.append(("", "\n"))
            return result

        kb = SelectKB()

        @kb.add("up")
        def _up(event: Any) -> None:
            selected[0] = (selected[0] - 1) % len(options)

        @kb.add("down")
        def _down(event: Any) -> None:
            selected[0] = (selected[0] + 1) % len(options)

        @kb.add("enter")
        def _accept(event: Any) -> None:
            event.app.exit(result=options[selected[0]])

        @kb.add("escape")
        @kb.add("c-c")
        def _cancel(event: Any) -> None:
            event.app.exit(result=None)

        layout = Layout(
            Window(
                FormattedTextControl(get_text),
                dont_extend_height=True,
            )
        )
        style = Style.from_dict(
            {
                "highlight": "bold fg:ansigreen",
                "option": "fg:ansibrightblack",
            }
        )

        app: Application[str | None] = Application(
            layout=layout,
            key_bindings=kb,
            style=style,
            full_screen=False,
        )

        self.console.print(f"[bold]{title}[/bold]")
        try:
            result = await app.run_async()
        except (EOFError, KeyboardInterrupt):
            result = None

        if result is not None:
            self.console.print(f"[dim]  → {result}[/dim]")
        return result

    async def _approval_prompt(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        """Show arrow-key approval selector.

        Options: Yes / Yes, this session / No
        'Yes, this session' auto-approves that tool type for rest of session.
        """
        # Check session-level auto-approve
        if tool_name in self._session_approved_tools:
            self.renderer.print_tool_call(tool_name, "pending", "(auto-approved)")
            return True

        self.renderer.print_approval_context(tool_name, arguments)

        result = await self._arrow_select(
            "Allow?",
            ["Yes", "Yes, this session", "No"],
            default_index=0,
        )

        if result is None or result == "No":
            self.renderer.print_system("Denied.")
            return False

        if result == "Yes":
            if tool_name == "run_command" and self._approval_manager:
                self._approval_manager.enable_shell()
            return True

        if result == "Yes, this session":
            self._session_approved_tools.add(tool_name)
            if self._approval_manager:
                self._approval_manager.enable_shell()
            return True

        return False

    async def _ask_user_prompt(
        self,
        question: str,
        options: list[str],
        allow_text: bool,
    ) -> str:
        """Show question with arrow-key option selection or free-text input."""
        if options:
            choices = list(options)
            if allow_text:
                choices.append("[Type answer]")

            result = await self._arrow_select(question, choices)

            if result == "[Type answer]":
                try:
                    answer = await self._ensure_prompt_session().prompt_async("Answer: ")
                    return answer.strip()
                except (EOFError, KeyboardInterrupt):
                    return ""

            if result is not None:
                return result

            return options[0] if options else ""
        else:
            # Free-text only
            self.console.print(f"[bold]{question}[/bold]")
            try:
                answer = await self._ensure_prompt_session().prompt_async("Answer: ")
                return answer.strip()
            except (EOFError, KeyboardInterrupt):
                return ""
