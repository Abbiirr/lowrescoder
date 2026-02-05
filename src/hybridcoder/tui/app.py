"""Main Textual TUI application for HybridCoder."""

from __future__ import annotations

import asyncio
import difflib
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static, TextArea

from hybridcoder.config import HybridCoderConfig, load_config
from hybridcoder.session.store import SessionStore
from hybridcoder.tui.commands import CommandRouter, create_default_router
from hybridcoder.tui.file_completer import expand_references
from hybridcoder.tui.widgets.chat_view import ChatView
from hybridcoder.tui.widgets.input_bar import InputBar
from hybridcoder.tui.widgets.status_bar import StatusBar

if TYPE_CHECKING:
    from hybridcoder.agent.approval import ApprovalManager
    from hybridcoder.agent.loop import AgentLoop
    from hybridcoder.agent.tools import ToolRegistry
    from hybridcoder.layer4.llm import OllamaProvider, OpenRouterProvider

logger = logging.getLogger(__name__)


class HybridCoderApp(App[None]):
    """HybridCoder TUI application."""

    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("ctrl+d", "quit", "Quit", show=False),
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("ctrl+t", "toggle_thinking", "Toggle thinking", show=False),
        Binding("alt+t", "toggle_thinking", "Toggle thinking", show=False),
        Binding("pageup", "page_up", "Scroll up", show=False),
        Binding("pagedown", "page_down", "Scroll down", show=False),
    ]

    def __init__(
        self,
        config: HybridCoderConfig | None = None,
        session_id: str | None = None,
        project_root: Path | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.config = config or load_config()
        self.project_root = project_root or Path.cwd()
        self.session_store = SessionStore(self.config.tui.session_db_path)
        self.session_id = session_id or ""
        self.command_router: CommandRouter = create_default_router()
        self._provider: OllamaProvider | OpenRouterProvider | None = None
        self._agent_loop: AgentLoop | None = None
        self._tool_registry: ToolRegistry | None = None
        self._approval_manager: ApprovalManager | None = None
        self._generating = False
        self._show_thinking = True  # Show thinking tokens by default
        self._session_titled = False  # Track if session has been auto-titled
        self._ask_user_future: asyncio.Future[str] | None = None

    def compose(self) -> ComposeResult:
        yield Static(
            f" HybridCoder ({self.config.llm.provider}:{self.config.llm.model})",
            id="header",
        )
        yield ChatView(id="chat-view")
        yield InputBar(id="input-bar")
        yield StatusBar(id="status-bar")

    def on_mount(self) -> None:
        # Create or resume session
        if not self.session_id:
            title = f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            self.session_id = self.session_store.create_session(
                title=title,
                model=self.config.llm.model,
                provider=self.config.llm.provider,
                project_dir=str(self.project_root),
            )
        else:
            self._session_titled = True  # Resumed sessions keep their title

        # Update status bar
        status = self.query_one("#status-bar", StatusBar)
        status.model = self.config.llm.model
        status.mode = self.config.tui.approval_mode

        # Wire autocomplete into input bar
        input_bar = self.query_one("#input-bar", InputBar)
        cmd_names = [cmd.name for cmd in self.command_router.get_all()]
        # Include aliases too
        for cmd in self.command_router.get_all():
            cmd_names.extend(cmd.aliases)
        input_bar.set_completions(cmd_names, self.project_root)

        # Bench mode sentinel
        if os.environ.get("HYBRIDCODER_BENCH") == "1":
            print("BENCH:READY")  # noqa: T201

    def _ensure_agent_loop(self) -> AgentLoop:
        """Lazy-initialize the agent loop with all dependencies."""
        if self._agent_loop is not None:
            return self._agent_loop

        from hybridcoder.agent.approval import ApprovalManager, ApprovalMode
        from hybridcoder.agent.loop import AgentLoop
        from hybridcoder.agent.tools import create_default_registry
        from hybridcoder.layer4.llm import create_provider

        if self._provider is None:
            self._provider = create_provider(self.config)

        self._tool_registry = create_default_registry(project_root=str(self.project_root))
        self._approval_manager = ApprovalManager(
            mode=ApprovalMode(self.config.tui.approval_mode),
            shell_config=self.config.shell,
        )

        # Load project memory if available
        memory_content = None
        memory_file = self.project_root / ".hybridcoder" / "memory.md"
        if memory_file.exists():
            try:
                memory_content = memory_file.read_text(encoding="utf-8")
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

    @staticmethod
    def _generate_title(message: str) -> str:
        """Generate a human-readable session title from a user message.

        Strategy: clean the message, take the first ~6 words, capitalize.
        Similar to how Claude Code and Codex auto-title sessions.
        """
        text = re.sub(r"@\S+", "", message)  # remove @file references
        text = re.sub(r"```[\s\S]*?```", "", text)  # remove code blocks
        text = re.sub(r"[*_`#]", "", text)  # remove markdown formatting
        text = re.sub(r"\s+", " ", text).strip()  # normalize whitespace
        words = text.split()[:6]
        if not words:
            return f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        title = " ".join(words)
        if len(text.split()) > 6:
            title += "..."
        return title[0].upper() + title[1:] if title else "New session"

    async def on_input_bar_submitted(self, event: InputBar.Submitted) -> None:
        """Handle submitted text from the input bar."""
        text = event.text
        logger.debug("on_input_bar_submitted: %s", text[:80])

        # If ask_user is waiting for free-text, resolve the future
        if self._ask_user_future is not None and not self._ask_user_future.done():
            self._ask_user_future.set_result(text)
            chat = self.query_one("#chat-view", ChatView)
            chat.add_message("user", text)
            return

        # Try slash command first
        result = self.command_router.dispatch(text)
        if result is not None:
            cmd, args = result
            await cmd.handler(self, args)
            return

        # Expand @file references
        text = expand_references(text, self.project_root)

        # Send to agent loop (non-blocking via @work)
        self._run_agent(text)

    @work(exclusive=True)
    async def _run_agent(self, user_message: str) -> None:
        """Run the agent loop for a user message.

        Uses @work(exclusive=True) to keep the UI responsive during
        LLM generation. Previous runs are auto-cancelled.
        """
        chat = self.query_one("#chat-view", ChatView)
        chat.add_message("user", user_message)

        # Auto-title session from first user message
        if not self._session_titled:
            self._session_titled = True
            new_title = self._generate_title(user_message)
            self.session_store.update_session(self.session_id, title=new_title)

        agent_loop = self._ensure_agent_loop()
        # Update session ID in case it changed
        agent_loop.session_id = self.session_id

        self._generating = True
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.thinking = True
        chat.show_thinking()

        def on_chunk(chunk: str) -> None:
            chat.add_streaming_chunk(chunk)

        def on_thinking_chunk(chunk: str) -> None:
            if self._show_thinking:
                chat.add_thinking_chunk(chunk)

        def on_tool_call(name: str, status: str, result: str) -> None:
            if self.config.tui.show_tool_calls:
                chat.add_tool_call_display(name, status, result)

        async def approval_callback(tool_name: str, arguments: dict[str, Any]) -> bool:
            return await self._interactive_approval(tool_name, arguments)

        async def ask_user_cb(
            question: str, options: list[str], allow_text: bool,
        ) -> str:
            return await self._interactive_ask_user(question, options, allow_text)

        chat.start_streaming()
        try:
            response = await agent_loop.run(
                user_message,
                on_chunk=on_chunk,
                on_thinking_chunk=on_thinking_chunk,
                on_tool_call=on_tool_call,
                approval_callback=approval_callback,
                ask_user_callback=ask_user_cb,
            )
            chat.finish_streaming()
            chat.finish_thinking_stream()

            # Update token count
            if self._provider:
                status_bar.tokens += self._provider.count_tokens(response)
        except asyncio.CancelledError:
            chat.finish_streaming()
            chat.finish_thinking_stream()
            chat.add_message("system", "[Cancelled]")
        except Exception as e:
            chat.finish_streaming()
            chat.finish_thinking_stream()
            chat.add_message("system", f"Error: {e}")
        finally:
            self._generating = False
            status_bar.thinking = False
            status_bar.user_typing = False

    async def _interactive_approval(
        self, tool_name: str, arguments: dict[str, Any],
    ) -> bool:
        """Show an interactive approval prompt for tool calls.

        In auto mode: auto-approve (show diff for writes).
        In suggest mode: show Y/n/a prompt and wait for user response.
        In read-only mode: handled earlier by ApprovalManager.
        """
        from hybridcoder.agent.approval import ApprovalMode

        logger.debug("approval: tool=%s, mode=%s", tool_name, self.config.tui.approval_mode)
        mode = ApprovalMode(self.config.tui.approval_mode)

        # Auto mode: show diff preview, auto-approve
        if mode == ApprovalMode.AUTO:
            if tool_name == "write_file" and "content" in arguments:
                self._show_diff_preview(arguments.get("path", ""), arguments["content"])
            return True

        # Suggest mode: show interactive prompt
        chat = self.query_one("#chat-view", ChatView)

        # Build description of what the tool wants to do
        desc = self._format_tool_description(tool_name, arguments)

        # Show diff preview for write operations
        if tool_name == "write_file" and "content" in arguments:
            self._show_diff_preview(arguments.get("path", ""), arguments["content"])

        # Create future and approval prompt
        loop = asyncio.get_running_loop()
        future: asyncio.Future[tuple[str, bool]] = loop.create_future()

        from hybridcoder.tui.widgets.approval_prompt import ApprovalPrompt

        prompt_widget = ApprovalPrompt(
            tool_name, desc, future, classes="approval-prompt",
        )
        chat.mount(prompt_widget)
        chat.scroll_end(animate=False)

        # Wait for user response
        try:
            response, always = await future
        finally:
            prompt_widget.remove()
            self.query_one("#input-bar", InputBar).focus()

        # Handle "always" — switch to auto mode
        if always:
            self.config.tui.approval_mode = "auto"
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.mode = "auto"
            if self._approval_manager is not None:
                self._approval_manager.mode = ApprovalMode.AUTO
            chat.add_message("system", "Switched to auto mode (always allow).")

        return response == "yes"

    async def _interactive_ask_user(
        self, question: str, options: list[str], allow_text: bool,
    ) -> str:
        """Show an interactive question prompt for the ask_user tool.

        If options are provided, shows an OptionSelector widget.
        If no options (or allow_text with no options), waits for free-text input.
        """
        chat = self.query_one("#chat-view", ChatView)
        logger.debug("ask_user: q=%s, opts=%s, text=%s", question[:50], options, allow_text)

        if options:
            from hybridcoder.tui.widgets.approval_prompt import OptionSelector

            loop = asyncio.get_running_loop()
            future: asyncio.Future[list[str]] = loop.create_future()
            selector = OptionSelector(
                question, options, future, classes="option-selector",
            )
            chat.mount(selector)
            chat.scroll_end(animate=False)
            logger.debug("OptionSelector mounted, waiting for selection")

            try:
                selected = await future
            finally:
                selector.remove()
                self.query_one("#input-bar", InputBar).focus()

            logger.debug("OptionSelector result: %s", selected)
            if selected:
                return ", ".join(selected)
            return "(user skipped)"

        # Free-text mode: show question, wait for next InputBar submission
        logger.debug("Free-text mode, waiting for InputBar submit")
        chat.add_message("system", f"[bold]{question}[/]")
        loop = asyncio.get_running_loop()
        text_future: asyncio.Future[str] = loop.create_future()
        self._ask_user_future = text_future

        try:
            response = await text_future
        finally:
            self._ask_user_future = None

        return response if response else "(no response)"

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Update typing indicator when user types during generation."""
        if self._generating:
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.user_typing = bool(event.text_area.text.strip())

    def _format_tool_description(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Format a human-readable description of a tool call."""
        if tool_name == "write_file":
            path = arguments.get("path", "?")
            content = arguments.get("content", "")
            return f"Write {len(content)} chars to {path}"
        if tool_name == "run_command":
            cmd = arguments.get("command", "?")
            if not self.config.shell.enabled:
                return f"Enable shell and execute: {cmd}"
            return f"Execute: {cmd}"
        # Generic fallback
        args_str = ", ".join(f"{k}={v!r}" for k, v in list(arguments.items())[:3])
        return f"{tool_name}({args_str})"

    def _show_diff_preview(self, path: str, new_content: str) -> None:
        """Show a unified diff preview in the chat."""
        chat = self.query_one("#chat-view", ChatView)
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = self.project_root / file_path

        old_content = ""
        if file_path.exists():
            try:
                old_content = file_path.read_text(encoding="utf-8")
            except OSError:
                pass

        if old_content == new_content:
            return

        diff_lines = list(difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        ))
        if diff_lines:
            diff_text = "".join(diff_lines[:50])
            chat.add_message("system", f"```diff\n{diff_text}\n```")

    async def _stream_response(self, user_message: str) -> None:
        """Stream an LLM response (legacy, used when agent loop is not needed)."""
        chat = self.query_one("#chat-view", ChatView)
        chat.add_message("user", user_message)

        self.session_store.add_message(self.session_id, "user", user_message)

        if self._provider is None:
            from hybridcoder.layer4.llm import create_provider

            self._provider = create_provider(self.config)

        system_msg = "You are HybridCoder, an AI coding assistant. Be concise and helpful."
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_msg},
        ]
        for msg in self.session_store.get_messages(self.session_id):
            if msg.role in ("user", "assistant"):
                messages.append({"role": msg.role, "content": msg.content})

        self._generating = True
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.thinking = True
        chat.show_thinking()
        chat.start_streaming()
        try:
            async for chunk in self._provider.generate(messages, stream=True):
                if not self._generating:
                    break
                chat.add_streaming_chunk(chunk)
            full_text = chat.finish_streaming()

            self.session_store.add_message(self.session_id, "assistant", full_text)

            token_count = self._provider.count_tokens(full_text)
            status_bar.tokens += token_count
        except Exception as e:
            chat.finish_streaming()
            chat.add_message("system", f"Error: {e}")
        finally:
            self._generating = False
            status_bar.thinking = False

    def action_cancel(self) -> None:
        """Cancel ongoing generation or dismiss interactive widgets.

        If an interactive widget (OptionSelector, ApprovalPrompt) is active,
        resolve its future and dismiss it instead of cancelling the agent loop.
        """
        logger.debug("action_cancel triggered")
        from hybridcoder.tui.widgets.approval_prompt import ApprovalPrompt, OptionSelector

        # If interactive widgets are showing, dismiss them (don't cancel agent loop)
        for sel in self.query(OptionSelector):
            if hasattr(sel, "_future") and not sel._future.done():
                sel._future.set_result([])
            sel.remove()
            self.query_one("#input-bar", InputBar).focus()
            return
        for ap in self.query(ApprovalPrompt):
            if hasattr(ap, "_future") and not ap._future.done():
                ap._future.set_result(("no", False))
            ap.remove()
            self.query_one("#input-bar", InputBar).focus()
            return

        # No interactive widgets — cancel generation
        self._generating = False
        if self._agent_loop:
            self._agent_loop.cancel()
        # Also cancel any running worker
        self.workers.cancel_all()

    def action_toggle_thinking(self) -> None:
        """Toggle visibility of thinking/reasoning tokens (Ctrl+T / Alt+T)."""
        self._show_thinking = not self._show_thinking
        chat = self.query_one("#chat-view", ChatView)
        status = "shown" if self._show_thinking else "hidden"
        chat.add_message("system", f"Thinking tokens {status}")

    def action_page_up(self) -> None:
        """Scroll the chat view up by one page."""
        chat = self.query_one("#chat-view", ChatView)
        chat.scroll_relative(y=-chat.size.height)

    def action_page_down(self) -> None:
        """Scroll the chat view down by one page."""
        chat = self.query_one("#chat-view", ChatView)
        chat.scroll_relative(y=chat.size.height)

    async def action_quit(self) -> None:
        """Quit the application."""
        if os.environ.get("HYBRIDCODER_BENCH") == "1":
            print("BENCH:EXIT")  # noqa: T201
        self.exit()
