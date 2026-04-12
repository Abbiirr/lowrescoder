"""Inline REPL using Rich + prompt_toolkit.

Two modes:
- Parallel (CLI default): always-on prompt via `patch_stdout(raw=True)` so users can
  type while the assistant streams output above the prompt.
- Sequential: prompt -> response -> prompt, with blind type-ahead buffering during
  generation.

Bottom toolbar shows model/mode/tokens/edits. Thinking hidden by default.
"""

from __future__ import annotations

import asyncio
import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol, cast

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import ConditionalCompleter
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console

from autocode.agent.approval import ApprovalManager, ApprovalMode
from autocode.agent.event_recorder import EventRecorder
from autocode.agent.loop import AgentLoop, AgentMode
from autocode.agent.tools import ToolRegistry, create_default_registry
from autocode.config import AutoCodeConfig, load_config
from autocode.core.blob_store import BlobStore
from autocode.core.logging import setup_session_logging
from autocode.inline.completer import HybridAutoSuggest, HybridCompleter
from autocode.inline.renderer import InlineRenderer
from autocode.layer4.llm import create_provider
from autocode.session.episode_store import EpisodeStore
from autocode.session.store import SessionStore
from autocode.tui.commands import CommandRouter, create_default_router
from autocode.tui.file_completer import expand_references


class _MSVCRTModule(Protocol):
    """Subset of msvcrt we rely on for Escape/Ctrl+C detection.

    Mypy runs on non-Windows too; stubs for this Windows-only module can be
    incomplete/conditional. We cast to this protocol inside the Windows path.
    """

    def kbhit(self) -> bool: ...

    def getch(self) -> bytes: ...


@dataclass
class _PendingPromptRequest:
    """A pending interactive request that is fulfilled by the next submitted line.

    Used only in `--parallel` mode to avoid nested prompt_toolkit Applications.
    """

    kind: Literal["approval", "ask_user"]
    future: asyncio.Future[str]

    # Context used for parsing/UX.
    tool_name: str = ""
    question: str = ""
    options: list[str] = field(default_factory=list)
    allow_text: bool = False
    allow_session_approve: bool = True

    # Draft text that was in the main prompt when the request appeared.
    draft_text: str = ""
    draft_cursor: int = 0


class InlineApp:
    """Inline REPL using Rich + prompt_toolkit.

    This is the canonical rendering mode for AutoCode.
    Output goes to stdout (becomes terminal scrollback).
    Input handled by prompt_toolkit (async readline with completion).

    Sequential model: prompt -> process -> output -> prompt.
    Parallel model: prompt stays active while output streams above it.

    In sequential mode, we still capture "type-ahead" keystrokes and prefill the
    next prompt so user input isn't dropped during generation.
    """

    def __init__(
        self,
        config: AutoCodeConfig | None = None,
        session_id: str | None = None,
        project_root: Path | None = None,
        *,
        parallel: bool = False,
    ) -> None:
        self.config = config or load_config()
        self.project_root = project_root or Path.cwd()

        # Output
        self.console = Console()
        self.renderer = InlineRenderer(self.console)
        self.renderer._profile = self.config.ui.profile

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
        self._session_log_dir = setup_session_logging(self.config.logging, self.session_id)

        # Commands
        self.command_router: CommandRouter = create_default_router()

        # Input (prompt_toolkit) — lazy init in run() to avoid terminal detection in tests
        self.completer = HybridCompleter(self.command_router, self.project_root)
        self.auto_suggest = HybridAutoSuggest(self.command_router, self.project_root)
        self.session: PromptSession[str] | None = None

        # Agent (lazy init)
        self._provider: Any = None
        self._tool_registry: ToolRegistry | None = None
        self._approval_manager: ApprovalManager | None = None
        self._agent_loop: AgentLoop | None = None
        # Active per-turn agent task (tracks "generation in progress" independent
        # of whether the AgentLoop instance exists).
        self._agent_task: asyncio.Task[None] | None = None
        self._agent_finalizer_task: asyncio.Task[None] | None = None
        self._agent_cancel_message: str | None = None
        self._session_titled: bool = False
        self._interrupt_count: int = 0

        # Agent mode (persisted across loop recreation)
        self._agent_mode: AgentMode = AgentMode.NORMAL
        self._plan_mode_enabled: bool = False

        # Thinking visibility (hidden by default, matching Claude Code)
        self._show_thinking: bool = False

        # Session-level auto-approve tracking
        self._session_approved_tools: set[str] = set()
        self._session_stats: Any | None = None

        # Stats tracking
        self._total_tokens: int = 0
        self._edit_count: int = 0
        self._files_modified: set[str] = set()

        # Type-ahead capture while the agent is generating. In sequential mode
        # there is no visible prompt during generation, but we can still buffer
        # keystrokes so the next prompt is prefilled with what the user typed.
        self._typeahead_buffer: list[str] = []

        # `--parallel` mode: keep prompt active while output streams above it.
        self._parallel: bool = parallel
        self._pending_prompt_request: _PendingPromptRequest | None = None
        self._parallel_queue: deque[str] = deque()
        self._parallel_queue_max: int = 10
        self._parallel_shutdown: bool = False

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
        from autocode.tui.commands import _copy_to_clipboard

        return _copy_to_clipboard(text)

    async def run_loop_prompt(self, payload: str) -> None:
        """Execute a non-slash loop payload through the normal chat path."""
        await self._handle_input(payload)

    async def run_loop_command(self, payload: str) -> None:
        """Execute a slash-command loop payload through the command router."""
        result = self.command_router.dispatch(payload)
        if result is None:
            self.add_system_message(f"Unknown command: {payload}")
            return
        cmd, args = result
        await cmd.handler(self, args)

    def set_plan_mode(self, enabled: bool) -> None:
        """Set plan mode. Persists across agent loop recreation."""
        mode = AgentMode.PLANNING if enabled else AgentMode.NORMAL
        self.set_agent_mode(mode)

    def set_agent_mode(self, mode: AgentMode) -> None:
        """Set the persisted agent mode for the next/live loop."""
        self._agent_mode = mode
        self._plan_mode_enabled = mode == AgentMode.PLANNING
        if self._agent_loop:
            self._agent_loop.set_mode(mode)

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

        if self.config.ui.profile == "claude_like":
            # Claude Code style: model · tokens · mode
            parts = [model]
            if self._total_tokens > 0:
                if self._total_tokens >= 1000:
                    parts.append(f"{self._total_tokens / 1000:.1f}k tokens")
                else:
                    parts.append(f"{self._total_tokens} tokens")
            parts.append(mode)
            return " · ".join(parts)

        # Default style
        provider = self.config.llm.provider
        parts = [f"Model: {model}", f"Provider: {provider}", f"Mode: {mode}"]

        if self._parallel and self._parallel_queue:
            parts.append(f"Queued: {len(self._parallel_queue)}")

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

    def _get_status_toolbar(self) -> FormattedText:
        """Status line shown below the prompt (bottom toolbar)."""
        return FormattedText(
            [
                ("fg:ansibrightblack", f" {self._get_status_text()}"),
            ]
        )

    def _get_status_rprompt_text(self) -> str:
        """Short status for the right-aligned prompt (fallback for some terminals)."""
        model_short = self.config.llm.model.split("/")[-1]
        if model_short.endswith(":free"):
            model_short = model_short[: -len(":free")]
        # Keep the rprompt compact to reduce wrapping/overlap on narrow terminals.
        if len(model_short) > 18:
            model_short = model_short[:15] + "..."

        mode = self.approval_mode
        mode_short = {
            "read-only": "read-only",
            "suggest": "suggest",
            "auto": "auto",
            "autonomous": "autonomous",
        }.get(mode, mode)
        parts: list[str] = [model_short, mode_short]

        if self._parallel and self._parallel_queue:
            parts.append(f"Q{len(self._parallel_queue)}")

        if self._total_tokens > 0:
            if self._total_tokens >= 1000:
                token_str = f"~{self._total_tokens / 1000:.1f}k"
            else:
                token_str = f"~{self._total_tokens}"
            parts.append(token_str)

        if self._edit_count > 0:
            parts.append(f"E{self._edit_count}")
        if self._files_modified:
            parts.append(f"F{len(self._files_modified)}")

        return " ".join(parts)

    def _get_status_rprompt(self) -> FormattedText:
        """Status shown on the right side of the prompt line."""
        text = self._get_status_text()
        return FormattedText([("fg:ansibrightblack", text)])

    def _get_claude_like_bottom_toolbar(self) -> FormattedText:
        """Claude Code style bottom area: separator line + hints + status.

        Renders two lines below the prompt:
            ─────────────────────────────────
             ? for shortcuts            model · mode
        """
        try:
            from shutil import get_terminal_size

            width = max(40, get_terminal_size((80, 24)).columns - 1)
        except Exception:
            width = 80

        separator = "\u2500" * width
        hint = " ? for shortcuts"
        status = self._get_status_text().strip()
        # Pad hint and status to fill the width
        gap = width - len(hint) - len(status) - 1
        if gap < 1:
            gap = 1
        bottom_line = f"{hint}{' ' * gap}{status}"

        return FormattedText(
            [
                ("fg:ansibrightblack", separator),
                ("", "\n"),
                ("fg:ansibrightblack", bottom_line),
            ]
        )

    def _create_key_bindings(self) -> KeyBindings:
        """Create custom key bindings for the REPL."""
        kb = KeyBindings()

        @kb.add("s-tab")
        def _cycle_mode(event: Any) -> None:
            """Shift+Tab cycles approval modes."""
            modes = ["read-only", "suggest", "auto", "autonomous"]
            current = self.approval_mode
            idx = modes.index(current) if current in modes else 0
            self.approval_mode = modes[(idx + 1) % len(modes)]
            # Invalidate toolbar to show new mode
            event.app.invalidate()

        @kb.add("escape")
        def _escape(event: Any) -> None:
            """Escape cancels generation in `--parallel` mode (Claude Code parity)."""
            if self._parallel and self._agent_task is not None and not self._agent_task.done():
                event.app.create_background_task(
                    self._cancel_generation("[dim]Cancelled.[/dim]"),
                )

        return kb

    def _ensure_prompt_session(self) -> PromptSession[str]:
        """Create PromptSession lazily (avoids terminal detection during tests)."""
        if self.session is None:
            history_path = Path("~/.autocode/history").expanduser()
            history_path.parent.mkdir(parents=True, exist_ok=True)

            @Condition
            def _should_complete() -> bool:
                from prompt_toolkit.application import get_app
                text = get_app().current_buffer.text
                return text.startswith("/") or "@" in text

            # Subclass to override buffer height BEFORE layout creation.
            # prompt_toolkit captures _get_default_buffer_control_height at
            # layout build time in __init__, so we must override it on the
            # class before calling __init__.
            from prompt_toolkit.layout.dimension import Dimension as _Dim

            class _CompactPromptSession(PromptSession):
                def _get_default_buffer_control_height(self) -> _Dim:
                    return _Dim(min=1, max=1, preferred=1)

            # Claude Code style: separator + hints BELOW prompt; no rprompt.
            # Default style: status on the right (rprompt); no bottom toolbar.
            if self.config.ui.profile == "claude_like":
                bottom_toolbar_cb: Any = self._get_claude_like_bottom_toolbar
                rprompt_cb: Any = None
            else:
                bottom_toolbar_cb = None
                rprompt_cb = self._get_status_rprompt

            self.session = _CompactPromptSession(
                history=FileHistory(str(history_path)),
                completer=ConditionalCompleter(self.completer, _should_complete),
                auto_suggest=self.auto_suggest,
                multiline=False,
                complete_while_typing=True,
                bottom_toolbar=bottom_toolbar_cb,
                rprompt=rprompt_cb,
                key_bindings=self._create_key_bindings(),
                erase_when_done=True,
                reserve_space_for_menu=0,
            )
        return self.session

    async def run(self) -> None:
        """Main REPL loop. Blocks until /exit or Ctrl+D.

        Two modes:
        - Sequential (default): prompt -> agent -> prompt
        - Parallel (`--parallel`): keep the prompt active while the agent streams output.
        """
        prompt_session = self._ensure_prompt_session()
        self.renderer.print_welcome(
            model=self.config.llm.model,
            provider=self.config.llm.provider,
            mode=self.config.tui.approval_mode,
            profile=self.config.ui.profile,
        )

        input_prompt = FormattedText([("fg:ansigreen bold", "❯ ")])

        if self._parallel:
            await self._run_parallel(prompt_session, input_prompt)
        else:
            await self._run_sequential(prompt_session, input_prompt)

        self.renderer.print_goodbye()

    def _print_prompt_border(self, top: bool = True) -> None:
        """Print rounded border for the prompt input box (claude_like only)."""
        if self.config.ui.profile != "claude_like":
            return
        width = max(1, self.renderer._explicit_console_width() - 1)
        char = "╭" if top else "╰"
        # Claude Code uses #888 (secondaryBorder) for normal, #fd5db1 for bash
        self.renderer.console.print(f"[#888]{char}{'─' * (width - 2)}[/]")

    def _print_prompt_hints(self) -> None:
        """Print hint line below prompt box (claude_like only)."""
        if self.config.ui.profile != "claude_like":
            return
        self.renderer.console.print(
            "[dim]  ! for bash  ·  / for commands  ·  esc to undo[/dim]"
        )

    async def _run_sequential(
        self,
        prompt_session: PromptSession[str],
        input_prompt: FormattedText,
    ) -> None:
        """Sequential REPL loop (baseline cross-platform behavior)."""
        while True:
            try:
                typeahead = "".join(self._typeahead_buffer)
                self._typeahead_buffer.clear()
                if typeahead:
                    text = await prompt_session.prompt_async(input_prompt, default=typeahead)
                else:
                    text = await prompt_session.prompt_async(input_prompt)

                text = text.strip()
                if not text:
                    continue
                # With `erase_when_done=True`, the prompt input itself isn't left
                # in scrollback, so we re-print the submitted turn explicitly.
                self.renderer.print_user_turn(text)
                # Separator after user turn, before model output
                self.renderer.print_separator()
                self._interrupt_count = 0
                await self._handle_input_with_cancel(text)
                # Separator AFTER response, before next prompt
                self.renderer.print_turn_separator()
            except EOFError:
                break
            except KeyboardInterrupt:
                # Ctrl+C at the prompt should warn/exit. Ctrl+C during generation
                # is handled inside _handle_input_with_cancel(), but we still
                # guard here to avoid stale `_agent_loop` references causing the
                # wrong message at idle (Entry 114).
                if self._agent_task is not None and not self._agent_task.done():
                    if self._agent_loop:
                        self._agent_loop.cancel()
                    self._agent_task.cancel()
                    try:
                        await self._agent_task
                    except asyncio.CancelledError:
                        pass
                    self.renderer.end_thinking()
                    self.renderer.end_streaming()
                    self.console.print("[dim]^C — generation cancelled[/dim]")
                    self._typeahead_buffer.clear()
                    self._interrupt_count = 0
                    continue

                self.console.print(
                    "[dim]^C — Press Ctrl+C again to quit, or Ctrl+D[/dim]",
                )
                self._interrupt_count += 1
                if self._interrupt_count >= 2:
                    break
                continue

    async def _run_parallel(
        self,
        prompt_session: PromptSession[str],
        input_prompt: FormattedText,
    ) -> None:
        """Parallel REPL loop (always-on prompt while output streams).

        Uses `patch_stdout(raw=True)` so background output prints above the prompt.
        """
        from prompt_toolkit.patch_stdout import patch_stdout

        with patch_stdout(raw=True):
            self._parallel_shutdown = False
            self._parallel_queue.clear()

            # Ensure Rich prints go through the patched stdout proxy while the prompt is active.
            try:
                self.console.file = sys.stdout
            except Exception:
                pass

            while True:
                try:
                    raw = await prompt_session.prompt_async(input_prompt)
                except EOFError:
                    break
                except KeyboardInterrupt:
                    if self._generation_active():
                        await self._cancel_generation("[dim]^C — generation cancelled[/dim]")
                        self._interrupt_count = 0
                        continue

                    self.console.print(
                        "[dim]^C — Press Ctrl+C again to quit, or Ctrl+D[/dim]",
                    )
                    self._interrupt_count += 1
                    if self._interrupt_count >= 2:
                        break
                    continue

                text = raw.strip()

                # If the agent is awaiting an interactive response (approval/ask_user),
                # consume the submitted line for that request.
                if self._pending_prompt_request is not None:
                    self._handle_pending_prompt_submission(text)
                    continue

                if not text:
                    continue

                # Slash commands stay sequential (they control the app/session).
                if text.startswith("/"):
                    try:
                        await self._handle_input(text)
                    except EOFError:
                        break
                    self._interrupt_count = 0
                    continue

                # New message while generating: queue it (runs after current generation completes).
                if self._generation_active():
                    if len(self._parallel_queue) >= self._parallel_queue_max:
                        self.console.print(
                            "(queue full; dropping message)",
                            style="dim",
                            markup=False,
                        )
                    else:
                        self._parallel_queue.append(text)
                        self.console.print(
                            f"(queued {len(self._parallel_queue)} pending)",
                            style="dim",
                            markup=False,
                        )
                    self._interrupt_count = 0
                    continue

                self.renderer.print_user_turn(text)
                self.renderer.print_separator()
                self._interrupt_count = 0
                self._start_agent_task_parallel(text)

            # Exit: stop queue processing + cancel any active generation so we don't leak tasks.
            self._parallel_shutdown = True
            self._parallel_queue.clear()
            if self._generation_active():
                await self._cancel_generation(None)

    def _generation_active(self) -> bool:
        return self._agent_task is not None and not self._agent_task.done()

    def _start_agent_task_parallel(self, text: str) -> None:
        """Start the agent in the background and finalize the turn when done."""
        agent_task = asyncio.create_task(self._handle_input(text))
        self._agent_task = agent_task
        self._agent_finalizer_task = asyncio.create_task(
            self._finalize_agent_task_parallel(agent_task),
        )

    async def _finalize_agent_task_parallel(self, agent_task: asyncio.Task[None]) -> None:
        """Finalize a parallel agent run.

        Ensures any cancel message is printed, a turn separator is emitted,
        and per-turn task state is cleared.
        """
        try:
            await agent_task
        except asyncio.CancelledError:
            pass
        except EOFError:
            # Shouldn't happen for normal agent runs; ignore to avoid crashing the loop.
            pass
        except Exception as e:
            # `_run_agent()` already prints its own error; this is a last-resort guard.
            self.renderer.print_system(f"Error: {e}")
        finally:
            if self._agent_cancel_message:
                self.console.print(self._agent_cancel_message)
                self._agent_cancel_message = None

            # Separator after assistant output/cancel to keep "turn blocks" consistent.
            self.renderer.print_turn_separator()

            finalized_active = self._agent_task is agent_task
            if finalized_active:
                self._agent_task = None
            if self._agent_finalizer_task is asyncio.current_task():
                self._agent_finalizer_task = None

            # If messages were queued while generating, start the next one automatically.
            if (
                finalized_active
                and (not self._parallel_shutdown)
                and (self._pending_prompt_request is None)
                and self._parallel_queue
            ):
                next_text = self._parallel_queue.popleft()
                self.renderer.print_user_turn(next_text)
                self.renderer.print_separator()
                self._interrupt_count = 0
                self._start_agent_task_parallel(next_text)

    async def _cancel_generation(self, message: str | None) -> None:
        """Cancel the active generation and wait for cleanup (parallel mode)."""
        if not self._generation_active():
            return

        self._parallel_queue.clear()
        self._agent_cancel_message = message

        # If we were waiting for approval/ask_user, cancel that prompt request and restore draft.
        if self._pending_prompt_request is not None:
            pending = self._pending_prompt_request
            self._pending_prompt_request = None
            if not pending.future.done():
                pending.future.cancel()
            self._restore_prompt_draft(pending.draft_text, pending.draft_cursor)

        if self._agent_loop:
            self._agent_loop.cancel()

        assert self._agent_task is not None
        self._agent_task.cancel()
        try:
            await self._agent_task
        except asyncio.CancelledError:
            pass

        if self._agent_finalizer_task is not None:
            try:
                await self._agent_finalizer_task
            except asyncio.CancelledError:
                pass

    def _stash_prompt_draft(self) -> tuple[str, int]:
        """Capture current prompt buffer text (draft) and clear it."""
        if self.session is None:
            return ("", 0)
        try:
            buf = self.session.app.current_buffer
            text = buf.text
            cursor = buf.cursor_position
            buf.text = ""
            buf.cursor_position = 0
            self.session.app.invalidate()
            return (text, cursor)
        except Exception:
            return ("", 0)

    def _restore_prompt_draft(self, text: str, cursor: int) -> None:
        """Restore a previously stashed draft into the prompt buffer."""
        if self.session is None:
            return
        try:
            buf = self.session.app.current_buffer
            buf.text = text
            buf.cursor_position = min(max(0, cursor), len(text))
            self.session.app.invalidate()
        except Exception:
            return

    def _handle_pending_prompt_submission(self, text: str) -> None:
        """Handle the submitted line for a pending parallel prompt request."""
        req = self._pending_prompt_request
        if req is None or req.future.done():
            return

        if req.kind == "approval":
            answer = text.strip().lower()
            if answer in ("y", "yes"):
                req.future.set_result("yes")
                return
            if req.allow_session_approve and answer in (
                "s", "session", "this session", "yes, this session",
            ):
                req.future.set_result("session")
                return
            if answer in ("n", "no"):
                req.future.set_result("no")
                return
            if req.allow_session_approve:
                self.console.print(
                    "[dim]Allow? Type 'y' (yes), 's' (session), or 'n' (no).[/dim]"
                )
            else:
                self.console.print("[dim]Apply this edit? Type 'y' or 'n'.[/dim]")
            return

        if req.kind == "ask_user":
            if not req.options:
                req.future.set_result(text)
                return

            answer = text.strip()
            if answer.isdigit():
                idx = int(answer)
                if 1 <= idx <= len(req.options):
                    req.future.set_result(req.options[idx - 1])
                    return

            for opt in req.options:
                if answer == opt:
                    req.future.set_result(opt)
                    return

            if req.allow_text:
                req.future.set_result(text)
                return

            self.console.print(
                f"[dim]Please choose 1-{len(req.options)} (or type the exact option).[/dim]",
            )
            return

    async def _handle_input_with_cancel(self, text: str) -> None:
        """Wrap _handle_input in a cancellable task with Escape listener."""
        # Slash commands don't need cancellation
        if text.startswith("/"):
            await self._handle_input(text)
            return

        agent_task: asyncio.Task[None] = asyncio.create_task(self._handle_input(text))
        escape_task: asyncio.Task[bool] = asyncio.create_task(self._listen_for_escape())
        self._agent_task = agent_task

        try:
            try:
                done, pending = await asyncio.wait(
                    [agent_task, escape_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
            except KeyboardInterrupt:
                # SIGINT during generation: cancel tasks and cleanly end the current
                # streaming line before returning to the prompt.
                if self._agent_loop:
                    self._agent_loop.cancel()
                for task in (agent_task, escape_task):
                    task.cancel()
                for task in (agent_task, escape_task):
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                self.renderer.end_thinking()
                self.renderer.end_streaming()
                self.console.print("[dim]^C — generation cancelled[/dim]")
                self._typeahead_buffer.clear()
                self._interrupt_count = 0
                return

            for pending_task in pending:
                pending_task.cancel()
                try:
                    await pending_task
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
                    self.console.print("[dim]Cancelled.[/dim]")
                    self._typeahead_buffer.clear()
                    self._interrupt_count = 0
                    return

            # Re-raise any agent_task exception
            if agent_task in done:
                agent_task.result()  # raises if failed
        finally:
            # Don't leave a stale task reference across turns.
            if self._agent_task is agent_task:
                self._agent_task = None

    def _poll_key_windows(self) -> str | None:
        """Check for keypress on Windows. Returns key byte or None.

        Note: In sequential mode, this is used while the agent is generating.
        """
        import msvcrt as msvcrt_mod

        msvcrt = cast(_MSVCRTModule, msvcrt_mod)

        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key in (b"\x1b", b"\x03"):
                return key.decode("latin-1")
        return None

    def _poll_key_unix(self, fd: int) -> str | None:
        """Check for keypress on Unix. Returns char or None.

        Note: In sequential mode, this is used while the agent is generating.
        """
        import select
        import sys

        ready, _, _ = select.select([fd], [], [], 0.05)
        if ready:
            ch = sys.stdin.read(1)
            if ch in ("\x1b", "\x03"):
                return ch
        return None

    def _poll_key_windows_typeahead(self) -> tuple[str, bool] | None:
        """Windows: return (ch, is_cancel) for type-ahead capture.

        - Esc/Ctrl+C -> (ch, True)
        - Backspace -> ('\\x08', False)
        - Extended keys (arrows/F-keys) are ignored (consume 2nd byte).
        - Printable chars are returned as (ch, False)
        """
        import msvcrt as msvcrt_mod

        msvcrt = cast(_MSVCRTModule, msvcrt_mod)

        if not msvcrt.kbhit():
            return None

        key = msvcrt.getch()

        # Escape or Ctrl+C -> cancel generation.
        if key in (b"\x1b", b"\x03"):
            return (key.decode("latin-1"), True)

        # Extended key: 2-byte sequence starting with 0x00 or 0xE0.
        if key in (b"\x00", b"\xe0"):
            # Consume/discard the second byte so it doesn't appear as input.
            try:
                msvcrt.getch()
            except Exception:
                pass
            return None

        # Backspace.
        if key == b"\x08":
            return ("\x08", False)

        # Regular character. Use latin-1 to avoid decode errors for arbitrary bytes.
        ch = key.decode("latin-1")
        if ch in ("\r", "\n"):
            return None
        if ch == "\t" or ch.isprintable():
            return (ch, False)
        return None

    def _poll_key_unix_typeahead(self, fd: int) -> tuple[str, bool] | None:
        """Unix: return (ch, is_cancel) for type-ahead capture.

        Uses select() + sys.stdin.read(1) in raw mode (set by caller).
        """
        import select
        import sys

        ready, _, _ = select.select([fd], [], [], 0.05)
        if not ready:
            return None

        ch = sys.stdin.read(1)

        # Escape sequences (arrows, etc.) start with ESC. Only treat a *lone*
        # ESC as cancel. If more bytes are immediately available, ignore it
        # as part of an escape sequence.
        if ch == "\x1b":
            extra_ready, _, _ = select.select([fd], [], [], 0.01)
            if extra_ready:
                # Drain the rest of the escape sequence bytes that are ready.
                while True:
                    more, _, _ = select.select([fd], [], [], 0)
                    if not more:
                        break
                    _ = sys.stdin.read(1)
                return None
            return (ch, True)

        if ch == "\x03":  # Ctrl+C
            return (ch, True)

        if ch in ("\x7f", "\x08"):  # backspace (DEL) or BS
            return (ch, False)

        if ch in ("\r", "\n"):
            return None

        if ch == "\t" or ch.isprintable():
            return (ch, False)
        return None

    async def _listen_for_escape(self) -> bool:
        """Listen for Escape key press. Returns True if pressed."""
        import sys

        loop = asyncio.get_running_loop()

        if sys.platform == "win32":
            self._typeahead_buffer.clear()
            while True:
                result = await loop.run_in_executor(None, self._poll_key_windows_typeahead)
                if result is not None:
                    ch, is_cancel = result
                    if is_cancel:
                        return True
                    if ch == "\x08":  # backspace
                        if self._typeahead_buffer:
                            self._typeahead_buffer.pop()
                    else:
                        self._typeahead_buffer.append(ch)
                await asyncio.sleep(0.05)
        else:
            import os

            fd = sys.stdin.fileno()
            if not os.isatty(fd):
                return False  # Not a TTY — can't listen for keys

            import termios
            import tty

            try:
                old_settings = termios.tcgetattr(fd)
            except termios.error:
                return False  # Not a TTY — can't listen for keys
            try:
                try:
                    tty.setraw(fd)
                except termios.error:
                    return False  # Not a TTY — can't switch to raw mode
                self._typeahead_buffer.clear()
                while True:
                    result = await loop.run_in_executor(
                        None, self._poll_key_unix_typeahead, fd,
                    )
                    if result is not None:
                        ch, is_cancel = result
                        if is_cancel:
                            return True
                        if ch in ("\x7f", "\x08"):  # backspace
                            if self._typeahead_buffer:
                                self._typeahead_buffer.pop()
                        else:
                            self._typeahead_buffer.append(ch)
                    await asyncio.sleep(0.05)
            finally:
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                except termios.error:
                    pass

    async def _handle_input(self, text: str) -> None:
        """Route input to slash command or agent loop."""
        stripped = text.strip()

        # Intercept bare picker-eligible commands BEFORE the text-dump
        # command router path. Non-bare forms (e.g. "/model coding") still
        # fall through to the handler below.
        if stripped in ("/model", "/m"):
            await self._model_picker()
            return
        if stripped == "/provider":
            await self._provider_picker()
            return
        if stripped in ("/mode", "/permissions"):
            await self._mode_picker()
            return
        if stripped in ("/sessions", "/s", "/resume"):
            await self._sessions_picker()
            return
        if stripped in ("/checkpoint", "/ckpt"):
            await self._checkpoint_picker()
            return
        if stripped == "/loop cancel":
            await self._loop_cancel_picker()
            return
        if stripped == "/copy pick":
            await self._copy_picker()
            return

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

    # --- Interactive pickers (bare /model, /provider, /mode) ---

    async def _model_picker(self) -> None:
        """Arrow-select picker for ``/model``.

        Queries the configured backend for available models, presents them
        via ``_arrow_select`` with the current model pre-highlighted, and
        applies the selection by setting ``config.llm.model``.
        """
        from autocode.tui.commands import _list_models, _prioritize_models

        provider = self.config.llm.provider
        api_base = self.config.llm.api_base
        current_model = self.config.llm.model

        available = _list_models(provider, api_base)
        if not available:
            self.renderer.print_system(
                f"Could not list models from **{provider}** ({api_base}). "
                f"Current model: `{current_model}`"
            )
            return

        # Sort: active first, then known aliases, then alphabetical
        displayed, _ = _prioritize_models(available, current_model)
        default_index = 0
        for i, name in enumerate(displayed):
            if name == current_model:
                default_index = i
                break

        chosen = await self._arrow_select(
            f"Select a model (current: {current_model})",
            displayed,
            default_index=default_index,
        )
        if chosen is None or chosen == current_model:
            return

        self.config.llm.model = chosen
        # Reset the agent loop so it picks up the new model on the next turn
        self._agent_loop = None
        self.renderer.print_system(f"Switched model to: **{chosen}**")

    async def _provider_picker(self) -> None:
        """Arrow-select picker for ``/provider``."""
        from autocode.tui.commands import _SUPPORTED_PROVIDERS

        providers = list(_SUPPORTED_PROVIDERS)
        current = self.config.llm.provider

        default_index = 0
        for i, name in enumerate(providers):
            if name == current:
                default_index = i
                break

        chosen = await self._arrow_select(
            f"Select a provider (current: {current})",
            providers,
            default_index=default_index,
        )
        if chosen is None or chosen == current:
            return

        self.config.llm.provider = chosen
        self._agent_loop = None
        self.renderer.print_system(f"Switched provider to: **{chosen}**")

    async def _mode_picker(self) -> None:
        """Arrow-select picker for ``/mode`` (approval mode)."""
        modes = ["read-only", "suggest", "auto", "autonomous"]
        current = self.approval_mode

        default_index = 0
        for i, name in enumerate(modes):
            if name == current:
                default_index = i
                break

        chosen = await self._arrow_select(
            f"Select approval mode (current: {current})",
            modes,
            default_index=default_index,
        )
        if chosen is None or chosen == current:
            return

        self.approval_mode = chosen
        self.renderer.print_system(f"Switched to **{chosen}** mode.")

    async def _loop_cancel_picker(self) -> None:
        """Arrow-select picker for ``/loop cancel`` with no args.

        Lists currently active recurring-loop jobs so the user can pick
        which one to cancel instead of typing a numeric job id. Falls
        back to a helpful message when no jobs are active.
        """
        jobs_attr: dict = getattr(self, "_loop_jobs", None)  # type: ignore[assignment]
        if not jobs_attr:
            self.renderer.print_system("No active loop jobs.")
            return

        # Snapshot to avoid mutation during the picker
        active = sorted(jobs_attr.values(), key=lambda j: getattr(j, "id", 0))
        if not active:
            self.renderer.print_system("No active loop jobs.")
            return

        def _fmt(job) -> str:  # type: ignore[no-untyped-def]
            jid = getattr(job, "id", "?")
            payload = str(getattr(job, "payload", "") or "")
            interval = getattr(job, "interval_seconds", 0)
            runs = getattr(job, "run_count", 0)
            status = "running" if getattr(job, "running", False) else "idle"
            if getattr(job, "cancelled", False):
                status = "cancelled"
            short_payload = payload if len(payload) <= 50 else payload[:47] + "..."
            return f"#{jid}  every {interval}s  {status}  runs={runs}  {short_payload}"

        display = [_fmt(j) for j in active]
        cancel_entry = "Cancel — do not touch any loop"
        display.append(cancel_entry)

        chosen = await self._arrow_select(
            "Select a loop job to cancel",
            display,
            default_index=0,
        )
        if chosen is None or chosen == cancel_entry:
            return

        # Parse job id back out: display starts with "#NN  "
        try:
            jid = int(chosen.split()[0].lstrip("#"))
        except (ValueError, IndexError):
            self.renderer.print_system("Could not parse job id from selection")
            return

        # Delegate to the existing /loop cancel handler which owns the
        # real cancellation + cleanup lifecycle
        result = self.command_router.dispatch(f"/loop cancel {jid}")
        if result is not None:
            cmd, args = result
            await cmd.handler(self, args)

    async def _copy_picker(self) -> None:
        """Arrow-select picker for ``/copy pick``.

        Shows the recent assistant messages with a short preview so the
        user can pick which one to copy instead of counting N from the
        end and typing ``/copy 3``. Preserves the existing ``/copy``,
        ``/copy all``, ``/copy last N`` text paths — this only
        intercepts the explicit ``/copy pick`` spelling.
        """
        try:
            messages = self.session_store.get_messages(self.session_id)
        except Exception as exc:  # noqa: BLE001
            self.renderer.print_system(f"Could not load messages: {exc}")
            return

        assistant_msgs = [m for m in messages if m.role == "assistant"]
        if not assistant_msgs:
            self.renderer.print_system("No assistant messages to copy.")
            return

        # Show most recent first, up to 15 entries
        limit = 15
        recent = list(reversed(assistant_msgs))[:limit]

        display: list[str] = []
        for i, m in enumerate(recent, start=1):
            content = (m.content or "").strip().replace("\n", " ")
            preview = content if len(content) <= 60 else content[:57] + "..."
            display.append(f"#{i}  {preview}")

        chosen = await self._arrow_select(
            "Select an assistant message to copy",
            display,
            default_index=0,
        )
        if chosen is None:
            return

        try:
            idx = int(chosen.split()[0].lstrip("#")) - 1
        except (ValueError, IndexError):
            self.renderer.print_system("Could not parse selection")
            return
        if idx < 0 or idx >= len(recent):
            self.renderer.print_system("Selection out of range")
            return

        text = recent[idx].content or ""
        if self.copy_to_clipboard(text):
            self.renderer.print_system(
                f"Copied {len(text)} characters to clipboard."
            )
        else:
            preview = text[:500]
            if len(text) > 500:
                preview += "\n...(truncated)"
            self.renderer.print_system(
                f"Clipboard unavailable. Text:\n```\n{preview}\n```"
            )

    async def _checkpoint_picker(self) -> None:
        """Arrow-select picker for ``/checkpoint`` / ``/ckpt``.

        Lists existing checkpoints (most recent first) with a synthetic
        "Save new checkpoint..." option at the top. Selecting a checkpoint
        restores it; selecting the save option prompts for a label and
        creates a new checkpoint. Non-bare forms like
        ``/checkpoint save <label>`` and ``/checkpoint restore <id>``
        still fall through to the existing text handler.
        """
        try:
            from autocode.session.checkpoint_store import CheckpointStore
            from autocode.session.models import ensure_tables
            from autocode.session.task_store import TaskStore
        except Exception as exc:  # noqa: BLE001
            self.renderer.print_system(f"Checkpoint store unavailable: {exc}")
            return

        try:
            conn = self.session_store.get_connection()
            ensure_tables(conn)
            cp_store = CheckpointStore(conn, self.session_id)
            checkpoints = cp_store.list_checkpoints()
        except Exception as exc:  # noqa: BLE001
            self.renderer.print_system(f"Could not load checkpoints: {exc}")
            return

        # Build picker options: Save new at top, then existing checkpoints
        save_label = "+ Save new checkpoint..."
        display: list[str] = [save_label]
        for cp in checkpoints[:20]:
            label = cp.label or "checkpoint"
            if len(label) > 40:
                label = label[:37] + "..."
            short_id = (cp.id or "")[:8] if cp.id else "????????"
            display.append(f"{short_id}  {label}  ({cp.created_at})")

        chosen = await self._arrow_select(
            "Select a checkpoint",
            display,
            default_index=1 if len(display) > 1 else 0,
        )
        if chosen is None:
            return

        # --- Save branch ---
        if chosen == save_label:
            # Use a second arrow_select for a handful of common labels,
            # plus a "type a label..." escape that falls back to the
            # existing /checkpoint save handler via the text path
            preset_labels = [
                "pre-edit",
                "before-test-run",
                "working-baseline",
                "cancel",
            ]
            label_choice = await self._arrow_select(
                "Choose a label (or Escape to cancel)",
                preset_labels,
                default_index=0,
            )
            if label_choice is None or label_choice == "cancel":
                return
            try:
                task_store = TaskStore(conn, self.session_id)
                cp_id = cp_store.save_checkpoint(task_store, label_choice)
            except Exception as exc:  # noqa: BLE001
                self.renderer.print_system(f"Checkpoint save failed: {exc}")
                return
            self.renderer.print_system(
                f"Checkpoint saved: **{cp_id[:8]}** ({label_choice})"
            )
            return

        # --- Restore branch ---
        chosen_short = chosen.split()[0] if chosen else ""
        match_id = None
        for cp in checkpoints:
            if cp.id and cp.id.startswith(chosen_short):
                match_id = cp.id
                break
        if match_id is None:
            self.renderer.print_system(f"Checkpoint not found: {chosen_short}")
            return

        try:
            task_store = TaskStore(conn, self.session_id)
            result = cp_store.restore_checkpoint(
                match_id, task_store, self.session_store
            )
        except Exception as exc:  # noqa: BLE001
            self.renderer.print_system(f"Restore failed: {exc}")
            return

        self.renderer.print_system(
            f"Restored checkpoint: **{result.get('label', '?')}**"
        )
        active_files = result.get("active_files") or []
        if active_files:
            self.renderer.print_system(
                f"Active files: {', '.join(active_files[:20])}"
            )

    async def _sessions_picker(self) -> None:
        """Arrow-select picker for ``/sessions`` / ``/resume``.

        Lists recent sessions with their short id, title, model, and a
        first-message preview. On selection, switches the app to that
        session (resumes it) and replays its message history.
        """
        sessions = self.session_store.list_sessions()
        if not sessions:
            self.renderer.print_system("No sessions to resume.")
            return

        # Build display strings for the picker. Keep them short so the
        # inline list stays readable.
        limit = 15
        display: list[str] = []
        for s in sessions[:limit]:
            title = (s.title or "Untitled")
            if len(title) > 40:
                title = title[:37] + "..."
            short_id = s.id[:8] if s.id else "????????"
            model = s.model or "?"
            display.append(f"{short_id}  {title}  ({model})")

        # Current session is pre-highlighted when present
        default_index = 0
        for i, s in enumerate(sessions[:limit]):
            if s.id == self.session_id:
                default_index = i
                break

        chosen = await self._arrow_select(
            "Select a session to resume",
            display,
            default_index=default_index,
        )
        if chosen is None:
            return

        # Parse the short id back out of the chosen display string
        chosen_short = chosen.split()[0] if chosen else ""
        match = None
        for s in sessions:
            if s.id.startswith(chosen_short):
                match = s
                break
        if match is None:
            self.renderer.print_system(f"Session not found: {chosen_short}")
            return

        if match.id == self.session_id:
            self.renderer.print_system(
                f"Already on session **{match.id[:8]}** ({match.title or 'Untitled'})."
            )
            return

        # Resume: swap session id, reset the agent loop, replay history
        self.session_id = match.id
        self._agent_loop = None
        self.renderer.print_system(
            f"Resumed session **{match.id[:8]}**: {match.title or 'Untitled'}"
        )
        try:
            messages = self.session_store.get_messages(match.id)
        except Exception as exc:  # noqa: BLE001
            self.renderer.print_system(f"Could not load session messages: {exc}")
            return
        if not messages:
            return
        # Show a short tail so the user sees the last turn context
        tail = messages[-6:]
        for m in tail:
            if m.role == "user":
                self.renderer.print_user_turn(m.content[:400])
            elif m.role == "assistant":
                self.renderer.print_assistant_message(m.content[:400])

    # --- Agent ---

    def _ensure_agent_loop(self) -> AgentLoop:
        """Lazy-initialize agent loop with all dependencies."""
        if self._agent_loop is None:
            self._provider = create_provider(self.config)
            from autocode.agent.tool_result_cache import ToolResultCache

            self._tool_result_cache = ToolResultCache()
            self._tool_registry = create_default_registry(
                project_root=str(self.project_root),
                tool_result_cache=self._tool_result_cache,
            )
            self._approval_manager = ApprovalManager(
                mode=ApprovalMode(self.config.tui.approval_mode),
                shell_config=self.config.shell,
            )

            # Load project memory if available
            memory_path = self.project_root / ".autocode" / "memory.md"
            memory_content = None
            if memory_path.exists():
                try:
                    memory_content = memory_path.read_text(encoding="utf-8")
                except OSError:
                    pass

            # Training-grade event recorder (opt-in)
            event_recorder: EventRecorder | None = None
            if self.config.logging.training.enabled:
                blob_dir = self._session_log_dir / self.config.logging.training.blob_dir
                blob_store = BlobStore(blob_dir)
                episode_store = EpisodeStore(
                    self.session_store.get_connection(),
                    self.session_id,
                    blob_store,
                    max_episodes=self.config.logging.training.max_episodes_per_session,
                )
                event_recorder = EventRecorder(episode_store)

            # Use shared factory for consistent runtime wiring
            from autocode.agent.factory import create_orchestrator

            self._agent_loop, self._session_stats = create_orchestrator(
                provider=self._provider,
                tool_registry=self._tool_registry,
                approval_manager=self._approval_manager,
                session_store=self.session_store,
                session_id=self.session_id,
                memory_content=memory_content,
                event_recorder=event_recorder,
                context_length=getattr(self.config.llm, "context_length", 8192),
                layer2_config=self.config.layer2,
            )

            # Apply persisted agent mode
            if self._agent_mode != AgentMode.NORMAL:
                self._agent_loop.set_mode(self._agent_mode)

        return self._agent_loop

    def _on_tool_call(self, tool_name: str, status: str, result: str = "") -> None:
        """Track tool stats and forward to renderer."""
        self.renderer.print_tool_call(
            tool_name, status, result,
            profile=self.config.ui.profile,
        )

        # Track edits and files modified
        if status in ("completed", "success") and tool_name in ("write_file", "edit_file"):
            self._edit_count += 1
            if result:
                first_line = result.split("\n", 1)[0].strip()
                for prefix in ("Written to ", "Edited ", "Created "):
                    if first_line.startswith(prefix):
                        first_line = first_line.removeprefix(prefix).strip()
                        break
                self._files_modified.add(first_line[:200])

    def _print_edit_preview(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Render a diff preview for write/edit approvals."""
        from autocode.agent.tools import preview_file_change

        self.renderer.print_approval_context(tool_name, {"path": arguments.get("path", "")})
        try:
            preview = preview_file_change(
                tool_name,
                arguments,
                project_root=str(self.project_root),
            )
        except Exception as e:
            self.renderer.print_system(f"[dim]Preview unavailable: {e}[/dim]")
            return

        if preview.conflict_message:
            self.renderer.print_system(
                "[bold yellow]Warning:[/bold yellow] "
                f"{preview.conflict_message}"
            )
        self.renderer.print_diff(preview.before, preview.after, preview.file_path)

    async def _run_agent(self, user_message: str) -> None:
        """Run agent loop and stream output via renderer."""
        # Don't reprint user message — prompt_toolkit already displayed it.
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

        if self._session_stats:
            self.renderer.print_session_summary(self._session_stats.summary())

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
        """Show tool approval prompt.

        Sequential mode uses arrow-key selector.
        `--parallel` uses a single-prompt typed response (y/s/n) to avoid nested
        prompt_toolkit Applications while a prompt is active.
        """
        if self._parallel:
            return await self._approval_prompt_parallel(tool_name, arguments)

        # Check session-level auto-approve
        if tool_name in self._session_approved_tools:
            self.renderer.print_tool_call(tool_name, "pending", "(auto-approved)", profile=self.config.ui.profile)
            return True

        is_edit = tool_name == "edit_file"
        if is_edit:
            self._print_edit_preview(tool_name, arguments)
            result = await self._arrow_select(
                "Apply this edit?",
                ["Apply", "Reject"],
                default_index=0,
            )
        else:
            self.renderer.print_approval_context(tool_name, arguments)
            result = await self._arrow_select(
                "Allow?",
                ["Yes", "Yes, this session", "No"],
                default_index=0,
            )

        if result is None or result in {"No", "Reject"}:
            self.renderer.print_system("Denied.")
            return False

        if result in {"Yes", "Apply"}:
            if tool_name == "run_command" and self._approval_manager:
                self._approval_manager.enable_shell()
            return True

        if result == "Yes, this session":
            self._session_approved_tools.add(tool_name)
            if self._approval_manager:
                self._approval_manager.enable_shell()
            return True

        return False

    async def _approval_prompt_parallel(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        """Parallel-mode approval prompt (typed y/s/n)."""
        # Check session-level auto-approve
        if tool_name in self._session_approved_tools:
            self.renderer.print_tool_call(tool_name, "pending", "(auto-approved)", profile=self.config.ui.profile)
            return True

        if self._pending_prompt_request is not None:
            # Shouldn't happen (agent awaits one interactive request at a time),
            # but avoid clobbering state.
            self.renderer.print_system("Error: already waiting for user input.")
            return False

        is_edit = tool_name == "edit_file"
        if is_edit:
            self._print_edit_preview(tool_name, arguments)
            self.console.print("[dim]Apply this edit? Type 'y' or 'n'.[/dim]")
        else:
            self.renderer.print_approval_context(tool_name, arguments)
            self.console.print("[dim]Allow? Type 'y' (yes), 's' (session), or 'n' (no).[/dim]")

        loop = asyncio.get_running_loop()
        fut: asyncio.Future[str] = loop.create_future()
        draft_text, draft_cursor = self._stash_prompt_draft()
        req = _PendingPromptRequest(
            kind="approval",
            future=fut,
            tool_name=tool_name,
            draft_text=draft_text,
            draft_cursor=draft_cursor,
            allow_session_approve=not is_edit,
        )
        self._pending_prompt_request = req

        try:
            result = await fut
        except asyncio.CancelledError:
            return False
        finally:
            # Clear request (if still ours) and restore any draft text.
            if self._pending_prompt_request is req:
                self._pending_prompt_request = None
            self._restore_prompt_draft(req.draft_text, req.draft_cursor)

        if result == "no":
            self.renderer.print_system("Denied.")
            return False

        if result == "session":
            self._session_approved_tools.add(tool_name)
            if self._approval_manager:
                self._approval_manager.enable_shell()
            return True

        # "yes"
        if tool_name == "run_command" and self._approval_manager:
            self._approval_manager.enable_shell()
        return True

    async def _ask_user_prompt(
        self,
        question: str,
        options: list[str],
        allow_text: bool,
    ) -> str:
        """Show question with option selection or free-text input."""
        if self._parallel:
            return await self._ask_user_prompt_parallel(question, options, allow_text)

        if options:
            choices = list(options)
            if allow_text:
                choices.append("[Type answer]")

            result = await self._arrow_select(question, choices)

            if result == "[Type answer]":
                try:
                    answer = await self._ensure_prompt_session().prompt_async("Answer: ")
                    answer = answer.strip()
                    if answer:
                        self.console.print(f"[dim]  → {answer}[/dim]")
                    return answer
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
                answer = answer.strip()
                if answer:
                    self.console.print(f"[dim]  → {answer}[/dim]")
                return answer
            except (EOFError, KeyboardInterrupt):
                return ""

    async def _ask_user_prompt_parallel(
        self,
        question: str,
        options: list[str],
        allow_text: bool,
    ) -> str:
        """Parallel-mode ask_user prompt (typed response)."""
        if self._pending_prompt_request is not None:
            self.renderer.print_system("Error: already waiting for user input.")
            return ""

        self.console.print(f"[bold]{question}[/bold]")
        if options:
            for i, opt in enumerate(options, 1):
                self.console.print(f"[dim]  {i}.[/dim] {opt}", highlight=False)
            if allow_text:
                self.console.print("[dim]  (or type a custom answer)[/dim]")
        else:
            self.console.print("[dim](type your answer)[/dim]")

        loop = asyncio.get_running_loop()
        fut: asyncio.Future[str] = loop.create_future()
        draft_text, draft_cursor = self._stash_prompt_draft()
        req = _PendingPromptRequest(
            kind="ask_user",
            future=fut,
            question=question,
            options=list(options),
            allow_text=allow_text,
            draft_text=draft_text,
            draft_cursor=draft_cursor,
        )
        self._pending_prompt_request = req

        try:
            answer = await fut
            return str(answer)
        except asyncio.CancelledError:
            return options[0] if options else ""
        finally:
            if self._pending_prompt_request is req:
                self._pending_prompt_request = None
            self._restore_prompt_draft(req.draft_text, req.draft_cursor)
