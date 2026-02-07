"""Tests for inline REPL type-ahead buffering helpers.

These tests focus on the low-level key pollers and the prompt prefill hook.
We don't attempt to simulate real terminal IO here.
"""

from __future__ import annotations

import sys
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
def inline_app(inline_config: HybridCoderConfig, tmp_path: Path) -> InlineApp:
    return InlineApp(config=inline_config, project_root=tmp_path)


class _FakeMSVCRT:
    def __init__(self, keys: list[bytes]) -> None:
        self._keys = list(keys)
        self.getch_calls = 0

    def kbhit(self) -> bool:
        return bool(self._keys)

    def getch(self) -> bytes:
        self.getch_calls += 1
        return self._keys.pop(0)


class TestWindowsTypeaheadPoller:
    def test_printable_char(self, inline_app: InlineApp, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = _FakeMSVCRT([b"a"])
        monkeypatch.setitem(sys.modules, "msvcrt", fake)
        assert inline_app._poll_key_windows_typeahead() == ("a", False)

    def test_cancel_escape(self, inline_app: InlineApp, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = _FakeMSVCRT([b"\x1b"])
        monkeypatch.setitem(sys.modules, "msvcrt", fake)
        assert inline_app._poll_key_windows_typeahead() == ("\x1b", True)

    def test_cancel_ctrl_c(self, inline_app: InlineApp, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = _FakeMSVCRT([b"\x03"])
        monkeypatch.setitem(sys.modules, "msvcrt", fake)
        assert inline_app._poll_key_windows_typeahead() == ("\x03", True)

    def test_backspace(self, inline_app: InlineApp, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = _FakeMSVCRT([b"\x08"])
        monkeypatch.setitem(sys.modules, "msvcrt", fake)
        assert inline_app._poll_key_windows_typeahead() == ("\x08", False)

    def test_extended_key_consumes_two_bytes(
        self, inline_app: InlineApp, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakeMSVCRT([b"\xe0", b"H"])
        monkeypatch.setitem(sys.modules, "msvcrt", fake)
        assert inline_app._poll_key_windows_typeahead() is None
        assert fake.getch_calls == 2

    @pytest.mark.parametrize("key", [b"\r", b"\n"])
    def test_enter_is_ignored(
        self, inline_app: InlineApp, monkeypatch: pytest.MonkeyPatch, key: bytes
    ) -> None:
        fake = _FakeMSVCRT([key])
        monkeypatch.setitem(sys.modules, "msvcrt", fake)
        assert inline_app._poll_key_windows_typeahead() is None


class TestUnixTypeaheadPoller:
    def test_printable_char(self, inline_app: InlineApp) -> None:
        fd = 0
        with patch("select.select", return_value=([fd], [], [])), patch(
            "sys.stdin.read", return_value="a"
        ):
            assert inline_app._poll_key_unix_typeahead(fd) == ("a", False)

    def test_ctrl_c_is_cancel(self, inline_app: InlineApp) -> None:
        fd = 0
        with patch("select.select", return_value=([fd], [], [])), patch(
            "sys.stdin.read", return_value="\x03"
        ):
            assert inline_app._poll_key_unix_typeahead(fd) == ("\x03", True)

    def test_lone_escape_is_cancel(self, inline_app: InlineApp) -> None:
        fd = 0
        # Initial ready, then no extra bytes -> treat as cancel.
        select_calls = iter([([fd], [], []), ([], [], [])])
        with patch("select.select", side_effect=lambda *a, **k: next(select_calls)), patch(
            "sys.stdin.read", return_value="\x1b"
        ):
            assert inline_app._poll_key_unix_typeahead(fd) == ("\x1b", True)

    def test_escape_sequence_is_ignored(self, inline_app: InlineApp) -> None:
        fd = 0
        # ESC then extra bytes available -> drain bytes and ignore.
        select_calls = iter(
            [
                ([fd], [], []),  # initial ready
                ([fd], [], []),  # extra_ready after ESC
                ([fd], [], []),  # drain byte 1
                ([fd], [], []),  # drain byte 2
                ([], [], []),  # stop draining
            ]
        )
        with patch("select.select", side_effect=lambda *a, **k: next(select_calls)), patch(
            "sys.stdin.read", side_effect=["\x1b", "[", "A"]
        ):
            assert inline_app._poll_key_unix_typeahead(fd) is None

    @pytest.mark.parametrize("ch", ["\x7f", "\x08"])
    def test_backspace(self, inline_app: InlineApp, ch: str) -> None:
        fd = 0
        with patch("select.select", return_value=([fd], [], [])), patch(
            "sys.stdin.read", return_value=ch
        ):
            assert inline_app._poll_key_unix_typeahead(fd) == (ch, False)

    @pytest.mark.parametrize("ch", ["\r", "\n"])
    def test_enter_is_ignored(self, inline_app: InlineApp, ch: str) -> None:
        fd = 0
        with patch("select.select", return_value=([fd], [], [])), patch(
            "sys.stdin.read", return_value=ch
        ):
            assert inline_app._poll_key_unix_typeahead(fd) is None


class TestPromptPrefill:
    @pytest.mark.asyncio()
    async def test_run_prefills_prompt_from_buffer(self, inline_app: InlineApp) -> None:
        """If type-ahead buffer is non-empty, run() passes it as default=..."""
        inline_app._typeahead_buffer = list("abc")

        mock_session = SimpleNamespace()
        mock_session.prompt_async = AsyncMock(side_effect=["hello", EOFError()])

        with (
            patch.object(inline_app, "_ensure_prompt_session", return_value=mock_session),
            patch.object(inline_app.renderer, "print_welcome"),
            patch.object(inline_app.renderer, "print_user_turn"),
            patch.object(inline_app.renderer, "print_separator"),
            patch.object(inline_app.renderer, "print_turn_separator"),
            patch.object(inline_app.renderer, "print_goodbye"),
            patch.object(inline_app, "_handle_input_with_cancel", new_callable=AsyncMock),
        ):
            await inline_app.run()

        # First prompt call should include default=abc
        first_call = mock_session.prompt_async.call_args_list[0]
        assert first_call.kwargs.get("default") == "abc"
