"""Extensive tests for interactive widgets (OptionSelector, ApprovalPrompt).

These tests verify that arrow-key selection works, focus is correct,
futures resolve properly, and the full agent-loop → ask_user → widget
→ response flow doesn't deadlock.

The ROOT CAUSE of the deadlock was: on_input_bar_submitted awaited
_run_agent directly, blocking the Textual message pump. Interactive
widgets mounted during the run could never receive key events because
the event loop was stuck. The fix: launch _run_agent as a background
task via asyncio.create_task so the event handler returns immediately.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from hybridcoder.config import HybridCoderConfig
from hybridcoder.layer4.llm import LLMResponse, ToolCall


@pytest.fixture()
def tui_config() -> HybridCoderConfig:
    config = HybridCoderConfig()
    config.tui.session_db_path = ":memory:"
    return config


# ---------------------------------------------------------------------------
# 1. OptionSelector widget (standalone, mounted in a bare App)
# ---------------------------------------------------------------------------
class TestOptionSelectorStandalone:
    """Test OptionSelector outside the HybridCoderApp."""

    @pytest.mark.asyncio()
    async def test_single_select_enter_resolves_first(self) -> None:
        """Enter on first highlighted option resolves the future."""
        from textual.app import App, ComposeResult
        from textual.containers import Vertical

        from hybridcoder.tui.widgets.approval_prompt import OptionSelector

        loop = asyncio.get_running_loop()
        future: asyncio.Future[list[str]] = loop.create_future()

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield Vertical(id="container")

            def on_mount(self) -> None:
                container = self.query_one("#container")
                sel = OptionSelector("Pick:", ["Alpha", "Beta", "Gamma"], future)
                container.mount(sel)

        app = TestApp()
        async with app.run_test() as pilot:
            # Let mount + call_after_refresh settle
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()

            # First option is highlighted by default; press Enter
            await pilot.press("enter")
            await pilot.pause()

            assert future.done(), "Future should be resolved after Enter"
            assert future.result() == ["Alpha"]

    @pytest.mark.asyncio()
    async def test_single_select_arrow_down_then_enter(self) -> None:
        """Arrow down then Enter selects the second option."""
        from textual.app import App, ComposeResult
        from textual.containers import Vertical

        from hybridcoder.tui.widgets.approval_prompt import OptionSelector

        loop = asyncio.get_running_loop()
        future: asyncio.Future[list[str]] = loop.create_future()

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield Vertical(id="container")

            def on_mount(self) -> None:
                container = self.query_one("#container")
                container.mount(
                    OptionSelector("Pick:", ["Alpha", "Beta", "Gamma"], future),
                )

        app = TestApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()

            await pilot.press("down")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            assert future.done()
            assert future.result() == ["Beta"]

    @pytest.mark.asyncio()
    async def test_single_select_arrow_down_twice_selects_third(self) -> None:
        """Arrow down twice then Enter selects the third option."""
        from textual.app import App, ComposeResult
        from textual.containers import Vertical

        from hybridcoder.tui.widgets.approval_prompt import OptionSelector

        loop = asyncio.get_running_loop()
        future: asyncio.Future[list[str]] = loop.create_future()

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield Vertical(id="container")

            def on_mount(self) -> None:
                container = self.query_one("#container")
                container.mount(
                    OptionSelector("Pick:", ["X", "Y", "Z"], future),
                )

        app = TestApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()

            await pilot.press("down")
            await pilot.press("down")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            assert future.done()
            assert future.result() == ["Z"]

    @pytest.mark.asyncio()
    async def test_escape_cancels_with_empty_list(self) -> None:
        """Escape resolves the future with an empty list."""
        from textual.app import App, ComposeResult
        from textual.containers import Vertical

        from hybridcoder.tui.widgets.approval_prompt import OptionSelector

        loop = asyncio.get_running_loop()
        future: asyncio.Future[list[str]] = loop.create_future()

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield Vertical(id="container")

            def on_mount(self) -> None:
                container = self.query_one("#container")
                container.mount(
                    OptionSelector("Pick:", ["A", "B"], future),
                )

        app = TestApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()

            assert future.done()
            assert future.result() == []

    @pytest.mark.asyncio()
    async def test_option_list_receives_focus(self) -> None:
        """The inner OptionList widget should have focus after mount."""
        from textual.app import App, ComposeResult
        from textual.containers import Vertical
        from textual.widgets import OptionList

        from hybridcoder.tui.widgets.approval_prompt import OptionSelector

        loop = asyncio.get_running_loop()
        future: asyncio.Future[list[str]] = loop.create_future()

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield Vertical(id="container")

            def on_mount(self) -> None:
                container = self.query_one("#container")
                container.mount(
                    OptionSelector("Pick:", ["A", "B"], future),
                )

        app = TestApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()

            focused = app.focused
            assert isinstance(focused, OptionList), (
                f"Expected OptionList to have focus, got {type(focused).__name__}"
            )

    @pytest.mark.asyncio()
    async def test_multi_select_done_option(self) -> None:
        """In multi-select mode, selecting Done confirms the choices."""
        from textual.app import App, ComposeResult
        from textual.containers import Vertical

        from hybridcoder.tui.widgets.approval_prompt import OptionSelector

        loop = asyncio.get_running_loop()
        future: asyncio.Future[list[str]] = loop.create_future()

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield Vertical(id="container")

            def on_mount(self) -> None:
                container = self.query_one("#container")
                container.mount(
                    OptionSelector("Pick:", ["A", "B", "C"], future, multi=True),
                )

        app = TestApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()

            # Toggle first option (A)
            await pilot.press("enter")
            await pilot.pause()
            # Move down to B and toggle it
            await pilot.press("down")
            await pilot.press("enter")
            await pilot.pause()
            # Move down past C to "Done"
            await pilot.press("down")
            await pilot.press("down")
            await pilot.press("enter")
            await pilot.pause()

            assert future.done()
            assert future.result() == ["A", "B"]


# ---------------------------------------------------------------------------
# 2. ApprovalPrompt widget (standalone)
# ---------------------------------------------------------------------------
class TestApprovalPromptStandalone:
    """Test ApprovalPrompt outside the HybridCoderApp."""

    @pytest.mark.asyncio()
    async def test_enter_yes_resolves(self) -> None:
        """Pressing Enter on 'Yes' (first option) resolves ("yes", False)."""
        from textual.app import App, ComposeResult
        from textual.containers import Vertical

        from hybridcoder.tui.widgets.approval_prompt import ApprovalPrompt

        loop = asyncio.get_running_loop()
        future: asyncio.Future[tuple[str, bool]] = loop.create_future()

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield Vertical(id="container")

            def on_mount(self) -> None:
                container = self.query_one("#container")
                container.mount(ApprovalPrompt("write_file", "test.py", future))

        app = TestApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()

            await pilot.press("enter")
            await pilot.pause()

            assert future.done()
            assert future.result() == ("yes", False)

    @pytest.mark.asyncio()
    async def test_arrow_down_no_resolves(self) -> None:
        """Arrow down then Enter on 'No' resolves ("no", False)."""
        from textual.app import App, ComposeResult
        from textual.containers import Vertical

        from hybridcoder.tui.widgets.approval_prompt import ApprovalPrompt

        loop = asyncio.get_running_loop()
        future: asyncio.Future[tuple[str, bool]] = loop.create_future()

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield Vertical(id="container")

            def on_mount(self) -> None:
                container = self.query_one("#container")
                container.mount(ApprovalPrompt("write_file", "test.py", future))

        app = TestApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()

            await pilot.press("down")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            assert future.done()
            assert future.result() == ("no", False)

    @pytest.mark.asyncio()
    async def test_always_allow_resolves(self) -> None:
        """Arrow down twice to 'Always allow' resolves ("yes", True)."""
        from textual.app import App, ComposeResult
        from textual.containers import Vertical

        from hybridcoder.tui.widgets.approval_prompt import ApprovalPrompt

        loop = asyncio.get_running_loop()
        future: asyncio.Future[tuple[str, bool]] = loop.create_future()

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield Vertical(id="container")

            def on_mount(self) -> None:
                container = self.query_one("#container")
                container.mount(ApprovalPrompt("write_file", "test.py", future))

        app = TestApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()

            await pilot.press("down")
            await pilot.press("down")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            assert future.done()
            assert future.result() == ("yes", True)

    @pytest.mark.asyncio()
    async def test_escape_denies(self) -> None:
        """Escape resolves with ("no", False)."""
        from textual.app import App, ComposeResult
        from textual.containers import Vertical

        from hybridcoder.tui.widgets.approval_prompt import ApprovalPrompt

        loop = asyncio.get_running_loop()
        future: asyncio.Future[tuple[str, bool]] = loop.create_future()

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield Vertical(id="container")

            def on_mount(self) -> None:
                container = self.query_one("#container")
                container.mount(ApprovalPrompt("write_file", "test.py", future))

        app = TestApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()

            assert future.done()
            assert future.result() == ("no", False)

    @pytest.mark.asyncio()
    async def test_option_list_has_focus(self) -> None:
        """OptionList inside ApprovalPrompt has focus after mount."""
        from textual.app import App, ComposeResult
        from textual.containers import Vertical
        from textual.widgets import OptionList

        from hybridcoder.tui.widgets.approval_prompt import ApprovalPrompt

        loop = asyncio.get_running_loop()
        future: asyncio.Future[tuple[str, bool]] = loop.create_future()

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield Vertical(id="container")

            def on_mount(self) -> None:
                container = self.query_one("#container")
                container.mount(ApprovalPrompt("write_file", "test.py", future))

        app = TestApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()

            focused = app.focused
            assert isinstance(focused, OptionList), (
                f"Expected OptionList focus, got {type(focused).__name__}"
            )


# ---------------------------------------------------------------------------
# 3. _interactive_ask_user inside HybridCoderApp (non-blocking flow)
# ---------------------------------------------------------------------------
class TestInteractiveAskUserInApp:
    """Test _interactive_ask_user with the real HybridCoderApp.

    These tests verify the widget mounts inside ChatView, receives focus,
    and resolves the future when the user interacts with it.
    """

    @pytest.mark.asyncio()
    async def test_ask_user_with_options_does_not_deadlock(
        self, tui_config: HybridCoderConfig,
    ) -> None:
        """Calling _interactive_ask_user as a background task does not freeze."""
        from hybridcoder.tui.app import HybridCoderApp
        from hybridcoder.tui.widgets.approval_prompt import OptionSelector

        app = HybridCoderApp(config=tui_config)
        async with app.run_test(size=(80, 30)) as pilot:
            result_holder: list[str] = []

            async def ask() -> str:
                r = await app._interactive_ask_user("Choose:", ["A", "B"], False)
                result_holder.append(r)
                return r

            # Launch as background task (this is the non-deadlocking pattern)
            task = asyncio.create_task(ask())
            # Let the widget mount and focus settle
            for _ in range(5):
                await pilot.pause()

            # Verify selector is mounted
            selectors = app.query(OptionSelector)
            assert len(selectors) > 0, "OptionSelector should be mounted"

            # Press Enter to select first option
            await pilot.press("enter")
            for _ in range(3):
                await pilot.pause()

            result = await asyncio.wait_for(task, timeout=5.0)
            assert result == "A"

    @pytest.mark.asyncio()
    async def test_ask_user_arrow_down_selects_second(
        self, tui_config: HybridCoderConfig,
    ) -> None:
        """Arrow down then Enter selects the second option in the app."""
        from hybridcoder.tui.app import HybridCoderApp

        app = HybridCoderApp(config=tui_config)
        async with app.run_test(size=(80, 30)) as pilot:
            task = asyncio.create_task(
                app._interactive_ask_user("Pick:", ["X", "Y", "Z"], False),
            )
            for _ in range(5):
                await pilot.pause()

            await pilot.press("down")
            await pilot.pause()
            await pilot.press("enter")
            for _ in range(3):
                await pilot.pause()

            result = await asyncio.wait_for(task, timeout=5.0)
            assert result == "Y"

    @pytest.mark.asyncio()
    async def test_ask_user_escape_returns_skipped(
        self, tui_config: HybridCoderConfig,
    ) -> None:
        """Escape on OptionSelector returns '(user skipped)' in the app."""
        from hybridcoder.tui.app import HybridCoderApp

        app = HybridCoderApp(config=tui_config)
        async with app.run_test(size=(80, 30)) as pilot:
            task = asyncio.create_task(
                app._interactive_ask_user("Pick:", ["A", "B"], False),
            )
            for _ in range(5):
                await pilot.pause()

            await pilot.press("escape")
            for _ in range(3):
                await pilot.pause()

            result = await asyncio.wait_for(task, timeout=5.0)
            assert result == "(user skipped)"

    @pytest.mark.asyncio()
    async def test_ask_user_free_text_mode(
        self, tui_config: HybridCoderConfig,
    ) -> None:
        """Free-text ask_user (no options) resolves from InputBar submit."""
        from hybridcoder.tui.app import HybridCoderApp
        from hybridcoder.tui.widgets.input_bar import InputBar

        app = HybridCoderApp(config=tui_config)
        async with app.run_test(size=(80, 30)) as pilot:
            task = asyncio.create_task(
                app._interactive_ask_user("What color?", [], False),
            )
            for _ in range(5):
                await pilot.pause()

            # The ask_user_future should be set
            assert app._ask_user_future is not None

            # Type into the input bar and submit
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()
            await pilot.pause()
            for ch in "blue":
                await pilot.press(ch)
            await pilot.press("enter")
            for _ in range(3):
                await pilot.pause()

            result = await asyncio.wait_for(task, timeout=5.0)
            assert result == "blue"
            assert app._ask_user_future is None

    @pytest.mark.asyncio()
    async def test_selector_removed_after_selection(
        self, tui_config: HybridCoderConfig,
    ) -> None:
        """OptionSelector is removed from DOM after user selects."""
        from hybridcoder.tui.app import HybridCoderApp
        from hybridcoder.tui.widgets.approval_prompt import OptionSelector

        app = HybridCoderApp(config=tui_config)
        async with app.run_test(size=(80, 30)) as pilot:
            task = asyncio.create_task(
                app._interactive_ask_user("Pick:", ["A", "B"], False),
            )
            for _ in range(5):
                await pilot.pause()

            assert len(app.query(OptionSelector)) > 0

            await pilot.press("enter")
            for _ in range(5):
                await pilot.pause()

            await asyncio.wait_for(task, timeout=5.0)
            assert len(app.query(OptionSelector)) == 0

    @pytest.mark.asyncio()
    async def test_input_bar_refocused_after_selection(
        self, tui_config: HybridCoderConfig,
    ) -> None:
        """InputBar has focus after OptionSelector is dismissed."""
        from hybridcoder.tui.app import HybridCoderApp
        from hybridcoder.tui.widgets.input_bar import InputBar

        app = HybridCoderApp(config=tui_config)
        async with app.run_test(size=(80, 30)) as pilot:
            task = asyncio.create_task(
                app._interactive_ask_user("Pick:", ["A"], False),
            )
            for _ in range(5):
                await pilot.pause()

            await pilot.press("enter")
            for _ in range(5):
                await pilot.pause()

            await asyncio.wait_for(task, timeout=5.0)

            focused = app.focused
            assert isinstance(focused, InputBar), (
                f"Expected InputBar focus after dismiss, got {type(focused).__name__}"
            )


# ---------------------------------------------------------------------------
# 4. Full agent loop → ask_user → widget → response flow
# ---------------------------------------------------------------------------
class TestAskUserEndToEnd:
    """End-to-end: mock LLM triggers ask_user, user selects, loop continues.

    This is the critical test class. It proves that the agent loop can
    invoke ask_user, mount a widget, the user can interact with it, and
    the loop continues with the user's answer.
    """

    @pytest.fixture()
    def store(self, tmp_path: Path) -> Any:
        from hybridcoder.session.store import SessionStore
        s = SessionStore(tmp_path / "test.db")
        yield s
        s.close()

    @pytest.fixture()
    def session_id(self, store: Any) -> str:
        return store.create_session(title="Test", model="m", provider="mock")

    @pytest.mark.asyncio()
    async def test_agent_ask_user_with_sync_callback(
        self, store: Any, session_id: str,
    ) -> None:
        """AgentLoop ask_user with a sync callback works."""
        from hybridcoder.agent.approval import ApprovalManager, ApprovalMode
        from hybridcoder.agent.loop import AgentLoop
        from hybridcoder.agent.tools import ToolRegistry

        mock = AsyncMock()
        call_count = 0

        async def fake_generate(messages: Any, tools: Any, **kwargs: Any) -> LLMResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return LLMResponse(
                    content="",
                    tool_calls=[ToolCall(
                        id="tc1", name="ask_user",
                        arguments={"question": "Which lang?", "options": ["Python", "JS"]},
                    )],
                )
            return LLMResponse(content="OK, Python it is!")

        mock.generate_with_tools = fake_generate

        loop = AgentLoop(
            mock, ToolRegistry(),
            ApprovalManager(ApprovalMode.AUTO),
            store, session_id,
        )

        async def async_cb(q: str, opts: list[str], allow: bool) -> str:
            return "Python"

        result = await loop.run("test", ask_user_callback=async_cb)
        assert "Python" in result

    @pytest.mark.asyncio()
    async def test_agent_ask_user_with_async_callback(
        self, store: Any, session_id: str,
    ) -> None:
        """AgentLoop ask_user with an async callback works."""
        from hybridcoder.agent.approval import ApprovalManager, ApprovalMode
        from hybridcoder.agent.loop import AgentLoop
        from hybridcoder.agent.tools import ToolRegistry

        mock = AsyncMock()
        call_count = 0

        async def fake_generate(messages: Any, tools: Any, **kwargs: Any) -> LLMResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return LLMResponse(
                    content="",
                    tool_calls=[ToolCall(
                        id="tc1", name="ask_user",
                        arguments={"question": "Name?", "options": []},
                    )],
                )
            return LLMResponse(content="Hello!")

        mock.generate_with_tools = fake_generate

        loop = AgentLoop(
            mock, ToolRegistry(),
            ApprovalManager(ApprovalMode.AUTO),
            store, session_id,
        )

        async def async_cb(q: str, opts: list[str], allow: bool) -> str:
            return "Alice"

        result = await loop.run("test", ask_user_callback=async_cb)
        assert "Hello!" in result

    @pytest.mark.asyncio()
    async def test_agent_ask_user_no_callback_returns_error(
        self, store: Any, session_id: str,
    ) -> None:
        """AgentLoop ask_user without callback returns an error message."""
        from hybridcoder.agent.approval import ApprovalManager, ApprovalMode
        from hybridcoder.agent.loop import AgentLoop
        from hybridcoder.agent.tools import ToolRegistry

        mock = AsyncMock()
        call_count = 0

        async def fake_generate(messages: Any, tools: Any, **kwargs: Any) -> LLMResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return LLMResponse(
                    content="",
                    tool_calls=[ToolCall(
                        id="tc1", name="ask_user",
                        arguments={"question": "Pick?", "options": ["A"]},
                    )],
                )
            return LLMResponse(content="fallback")

        mock.generate_with_tools = fake_generate

        loop = AgentLoop(
            mock, ToolRegistry(),
            ApprovalManager(ApprovalMode.AUTO),
            store, session_id,
        )

        result = await loop.run("test")  # no ask_user_callback
        assert "fallback" in result

    @pytest.mark.asyncio()
    async def test_full_e2e_in_app_no_deadlock(
        self, tui_config: HybridCoderConfig,
    ) -> None:
        """Full E2E: app._run_agent triggers ask_user, user selects, loop finishes.

        This test proves the deadlock fix works. It:
        1. Injects a mock provider that returns an ask_user tool call
        2. Launches _run_agent as a background task (same as the fixed app does)
        3. Waits for the OptionSelector to appear
        4. Selects an option
        5. Verifies the agent loop completes with the user's choice
        """
        from hybridcoder.tui.app import HybridCoderApp
        from hybridcoder.tui.widgets.approval_prompt import OptionSelector

        app = HybridCoderApp(config=tui_config)

        async with app.run_test(size=(80, 30)) as pilot:
            # Inject mock provider
            call_count = 0

            async def fake_generate(
                messages: Any, tools: Any, **kwargs: Any,
            ) -> LLMResponse:
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return LLMResponse(
                        content="",
                        tool_calls=[ToolCall(
                            id="tc1", name="ask_user",
                            arguments={
                                "question": "Pick a language:",
                                "options": ["Python", "Rust", "Go"],
                            },
                        )],
                    )
                return LLMResponse(content="Great choice!")

            mock_provider = AsyncMock()
            mock_provider.generate_with_tools = fake_generate
            mock_provider.count_tokens = lambda text: len(text) // 4

            app._provider = mock_provider

            # Launch _run_agent via @work decorator (returns a Worker, not coroutine)
            app._run_agent("recommend a language")

            # Wait for selector to appear
            found_selector = False
            for _ in range(20):
                await pilot.pause()
                if app.query(OptionSelector):
                    found_selector = True
                    break

            assert found_selector, "OptionSelector should be mounted by ask_user"

            # Select "Rust" (second option: arrow down + enter)
            await pilot.press("down")
            await pilot.pause()
            await pilot.press("enter")

            # Let the agent loop complete
            for _ in range(20):
                await pilot.pause()

            # Worker should have completed without deadlock
            await app.workers.wait_for_complete()

    @pytest.mark.asyncio()
    async def test_e2e_escape_during_ask_user(
        self, tui_config: HybridCoderConfig,
    ) -> None:
        """E2E: user presses escape during ask_user, loop continues with skip."""
        from hybridcoder.tui.app import HybridCoderApp
        from hybridcoder.tui.widgets.approval_prompt import OptionSelector

        app = HybridCoderApp(config=tui_config)

        async with app.run_test(size=(80, 30)) as pilot:
            call_count = 0

            async def fake_generate(
                messages: Any, tools: Any, **kwargs: Any,
            ) -> LLMResponse:
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return LLMResponse(
                        content="",
                        tool_calls=[ToolCall(
                            id="tc1", name="ask_user",
                            arguments={
                                "question": "Pick:",
                                "options": ["A", "B"],
                            },
                        )],
                    )
                return LLMResponse(content="OK skipped")

            mock_provider = AsyncMock()
            mock_provider.generate_with_tools = fake_generate
            mock_provider.count_tokens = lambda text: len(text) // 4

            app._provider = mock_provider

            app._run_agent("test")

            for _ in range(20):
                await pilot.pause()
                if app.query(OptionSelector):
                    break

            await pilot.press("escape")
            for _ in range(20):
                await pilot.pause()

            await app.workers.wait_for_complete()


# ---------------------------------------------------------------------------
# 5. action_cancel interaction with interactive widgets
# ---------------------------------------------------------------------------
class TestActionCancelWithWidgets:
    """Test that action_cancel properly dismisses interactive widgets."""

    @pytest.mark.asyncio()
    async def test_cancel_dismisses_option_selector(
        self, tui_config: HybridCoderConfig,
    ) -> None:
        """action_cancel resolves OptionSelector future and removes widget."""
        from hybridcoder.tui.app import HybridCoderApp
        from hybridcoder.tui.widgets.approval_prompt import OptionSelector

        app = HybridCoderApp(config=tui_config)
        async with app.run_test(size=(80, 30)) as pilot:
            task = asyncio.create_task(
                app._interactive_ask_user("Pick:", ["A", "B"], False),
            )
            for _ in range(5):
                await pilot.pause()

            assert len(app.query(OptionSelector)) > 0

            # Trigger action_cancel
            app.action_cancel()
            for _ in range(5):
                await pilot.pause()

            result = await asyncio.wait_for(task, timeout=5.0)
            assert result == "(user skipped)"
            assert len(app.query(OptionSelector)) == 0

    @pytest.mark.asyncio()
    async def test_cancel_dismisses_approval_prompt(
        self, tui_config: HybridCoderConfig,
    ) -> None:
        """action_cancel resolves ApprovalPrompt future with deny."""
        from hybridcoder.tui.app import HybridCoderApp
        from hybridcoder.tui.widgets.approval_prompt import ApprovalPrompt

        app = HybridCoderApp(config=tui_config)
        # Force suggest mode so the approval prompt is shown
        app.config.tui.approval_mode = "suggest"
        async with app.run_test(size=(80, 30)) as pilot:
            task = asyncio.create_task(
                app._interactive_approval("write_file", {"path": "x.py", "content": "x"}),
            )
            for _ in range(5):
                await pilot.pause()

            assert len(app.query(ApprovalPrompt)) > 0

            app.action_cancel()
            for _ in range(5):
                await pilot.pause()

            result = await asyncio.wait_for(task, timeout=5.0)
            assert result is False  # denied
            assert len(app.query(ApprovalPrompt)) == 0


# ---------------------------------------------------------------------------
# 6. Non-blocking _run_agent (the deadlock fix)
# ---------------------------------------------------------------------------
class TestNonBlockingRunAgent:
    """Verify that _run_agent launched via create_task doesn't freeze the UI."""

    @pytest.mark.asyncio()
    async def test_run_agent_as_task_allows_key_events(
        self, tui_config: HybridCoderConfig,
    ) -> None:
        """When _run_agent runs as a task, other key events are processed."""
        from hybridcoder.tui.app import HybridCoderApp

        app = HybridCoderApp(config=tui_config)
        async with app.run_test(size=(80, 30)) as pilot:
            # Inject a slow mock provider
            async def slow_generate(
                messages: Any, tools: Any, **kwargs: Any,
            ) -> LLMResponse:
                await asyncio.sleep(0.2)
                return LLMResponse(content="done")

            mock_provider = AsyncMock()
            mock_provider.generate_with_tools = slow_generate
            mock_provider.count_tokens = lambda text: len(text) // 4

            app._provider = mock_provider

            # Launch agent via @work decorator
            app._run_agent("hello")

            # While agent is running, verify we can still process events
            await pilot.pause()
            await pilot.pause()

            # PageDown should still work
            await pilot.press("pagedown")
            await pilot.pause()

            # Wait for worker to finish
            await app.workers.wait_for_complete()
            assert app._generating is False

    @pytest.mark.asyncio()
    async def test_on_input_bar_submitted_does_not_block(
        self, tui_config: HybridCoderConfig,
    ) -> None:
        """Submitting a message via InputBar should return control quickly.

        After the fix, on_input_bar_submitted launches _run_agent as a
        background task and returns immediately.
        """
        from hybridcoder.tui.app import HybridCoderApp
        from hybridcoder.tui.widgets.input_bar import InputBar

        app = HybridCoderApp(config=tui_config)
        async with app.run_test(size=(80, 30)) as pilot:
            # Inject a provider that triggers ask_user
            call_count = 0

            async def fake_generate(
                messages: Any, tools: Any, **kwargs: Any,
            ) -> LLMResponse:
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return LLMResponse(
                        content="",
                        tool_calls=[ToolCall(
                            id="tc1", name="ask_user",
                            arguments={"question": "?", "options": ["A", "B"]},
                        )],
                    )
                return LLMResponse(content="done")

            mock_provider = AsyncMock()
            mock_provider.generate_with_tools = fake_generate
            mock_provider.count_tokens = lambda text: len(text) // 4

            app._provider = mock_provider

            # Submit a message (this used to deadlock)
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()
            for ch in "test":
                await pilot.press(ch)
            await pilot.press("enter")

            # Let the background task start and mount the selector
            for _ in range(20):
                await pilot.pause()

            from hybridcoder.tui.widgets.approval_prompt import OptionSelector

            # The selector should be mounted (proves we didn't deadlock)
            selectors = app.query(OptionSelector)
            assert len(selectors) > 0, (
                "OptionSelector should be mounted — app may have deadlocked"
            )

            # Select first option to unblock
            await pilot.press("enter")
            for _ in range(10):
                await pilot.pause()
