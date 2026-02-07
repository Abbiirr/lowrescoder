"""Tests for InlineApp `--parallel` mode (always-on prompt)."""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from hybridcoder.config import HybridCoderConfig
from hybridcoder.inline.app import InlineApp


@pytest.fixture()
def inline_config(tmp_path: Path) -> HybridCoderConfig:
    config = HybridCoderConfig()
    config.tui.session_db_path = str(tmp_path / "test.db")
    return config


@pytest.fixture()
def parallel_app(inline_config: HybridCoderConfig, tmp_path: Path) -> InlineApp:
    return InlineApp(config=inline_config, project_root=tmp_path, parallel=True)


class TestParallelRunLoop:
    @pytest.mark.asyncio()
    async def test_parallel_queues_new_message_while_generating(
        self, parallel_app: InlineApp
    ) -> None:
        """A second message can be submitted while the first agent task is still running.

        The second message should be queued (not started) until the first completes.
        """

        stop_prompt = asyncio.Event()
        prompt_inputs: asyncio.Queue[str] = asyncio.Queue()
        prompt_inputs.put_nowait("hello")
        prompt_inputs.put_nowait("world")

        async def _prompt_impl(_: object) -> str:
            try:
                return prompt_inputs.get_nowait()
            except asyncio.QueueEmpty:
                await stop_prompt.wait()
                raise EOFError

        prompt_async = AsyncMock(side_effect=_prompt_impl)
        mock_session = SimpleNamespace(prompt_async=prompt_async)

        never_finish = asyncio.Event()

        async def _hang(_: str) -> None:
            await never_finish.wait()

        async def _wait_until(predicate: callable, timeout: float = 1.0) -> None:
            loop = asyncio.get_running_loop()
            deadline = loop.time() + timeout
            while loop.time() < deadline:
                if predicate():
                    return
                await asyncio.sleep(0.01)
            raise TimeoutError

        with (
            patch(
                "prompt_toolkit.patch_stdout.patch_stdout",
                return_value=contextlib.nullcontext(),
            ),
            patch.object(parallel_app, "_ensure_prompt_session", return_value=mock_session),
            patch.object(
                parallel_app,
                "_handle_input",
                new_callable=AsyncMock,
                side_effect=_hang,
            ) as mock_handle,
            patch.object(parallel_app.renderer, "print_welcome"),
            patch.object(parallel_app.renderer, "print_goodbye"),
            patch.object(parallel_app.renderer, "print_user_turn"),
            patch.object(parallel_app.renderer, "print_separator"),
            patch.object(parallel_app.renderer, "print_turn_separator"),
            patch.object(parallel_app.console, "print") as mock_print,
        ):
            run_task = asyncio.create_task(parallel_app.run())

            # Wait until we've accepted the second submitted message.
            await _wait_until(lambda: prompt_async.call_count >= 2, timeout=1.0)
            assert mock_handle.call_count == 1
            assert len(parallel_app._parallel_queue) == 1  # queued "world"

            # Ensure we provided user feedback that the message was queued.
            assert any(
                call.args and isinstance(call.args[0], str) and "queued" in call.args[0]
                for call in mock_print.call_args_list
            )

            stop_prompt.set()
            await asyncio.wait_for(run_task, timeout=1.0)

    @pytest.mark.asyncio()
    async def test_parallel_drains_queue_after_completion(
        self, parallel_app: InlineApp
    ) -> None:
        """Queued messages start automatically after the active generation completes."""

        stop_prompt = asyncio.Event()
        prompt_inputs: asyncio.Queue[str] = asyncio.Queue()
        prompt_inputs.put_nowait("hello")
        prompt_inputs.put_nowait("world")

        async def _prompt_impl(_: object) -> str:
            try:
                return prompt_inputs.get_nowait()
            except asyncio.QueueEmpty:
                await stop_prompt.wait()
                raise EOFError

        prompt_async = AsyncMock(side_effect=_prompt_impl)
        mock_session = SimpleNamespace(prompt_async=prompt_async)

        allow_first = asyncio.Event()
        allow_second = asyncio.Event()
        call_order: list[str] = []

        async def _controlled(text: str) -> None:
            call_order.append(text)
            if text == "hello":
                await allow_first.wait()
                return
            if text == "world":
                await allow_second.wait()
                return

        async def _wait_until(predicate: callable, timeout: float = 1.0) -> None:
            loop = asyncio.get_running_loop()
            deadline = loop.time() + timeout
            while loop.time() < deadline:
                if predicate():
                    return
                await asyncio.sleep(0.01)
            raise TimeoutError

        with (
            patch(
                "prompt_toolkit.patch_stdout.patch_stdout",
                return_value=contextlib.nullcontext(),
            ),
            patch.object(parallel_app, "_ensure_prompt_session", return_value=mock_session),
            patch.object(
                parallel_app,
                "_handle_input",
                new_callable=AsyncMock,
                side_effect=_controlled,
            ),
            patch.object(parallel_app.renderer, "print_welcome"),
            patch.object(parallel_app.renderer, "print_goodbye"),
            patch.object(parallel_app.renderer, "print_user_turn"),
            patch.object(parallel_app.renderer, "print_separator"),
            patch.object(parallel_app.renderer, "print_turn_separator"),
            patch.object(parallel_app.console, "print"),
        ):
            run_task = asyncio.create_task(parallel_app.run())

            # First message starts immediately; second is queued.
            await _wait_until(lambda: call_order == ["hello"], timeout=1.0)
            assert len(parallel_app._parallel_queue) == 1

            # Completing the first run should automatically start the queued message.
            allow_first.set()
            await _wait_until(lambda: call_order == ["hello", "world"], timeout=1.0)
            assert len(parallel_app._parallel_queue) == 0

            allow_second.set()
            stop_prompt.set()
            await asyncio.wait_for(run_task, timeout=1.0)
