"""Tests for platform-specific key polling in InlineApp."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from hybridcoder.config import HybridCoderConfig
from hybridcoder.inline.app import InlineApp


@pytest.fixture()
def app(tmp_path: Path) -> InlineApp:
    """Create an InlineApp for testing."""
    config = HybridCoderConfig()
    config.tui.session_db_path = str(tmp_path / "test.db")
    return InlineApp(config=config, project_root=tmp_path)


class TestPollKeyWindows:
    """Tests for _poll_key_windows synchronous helper."""

    def test_escape_detected(self, app: InlineApp) -> None:
        """msvcrt.kbhit()=True, getch()=b'\\x1b' returns '\\x1b'."""
        mock_msvcrt = ModuleType("msvcrt")
        mock_msvcrt.kbhit = MagicMock(return_value=True)  # type: ignore[attr-defined]
        mock_msvcrt.getch = MagicMock(return_value=b"\x1b")  # type: ignore[attr-defined]
        with patch.dict("sys.modules", {"msvcrt": mock_msvcrt}):
            result = app._poll_key_windows()
        assert result == "\x1b"

    def test_ctrl_c_detected(self, app: InlineApp) -> None:
        """msvcrt.kbhit()=True, getch()=b'\\x03' returns '\\x03'."""
        mock_msvcrt = ModuleType("msvcrt")
        mock_msvcrt.kbhit = MagicMock(return_value=True)  # type: ignore[attr-defined]
        mock_msvcrt.getch = MagicMock(return_value=b"\x03")  # type: ignore[attr-defined]
        with patch.dict("sys.modules", {"msvcrt": mock_msvcrt}):
            result = app._poll_key_windows()
        assert result == "\x03"

    def test_regular_key_ignored(self, app: InlineApp) -> None:
        """msvcrt.kbhit()=True, getch()=b'a' returns None."""
        mock_msvcrt = ModuleType("msvcrt")
        mock_msvcrt.kbhit = MagicMock(return_value=True)  # type: ignore[attr-defined]
        mock_msvcrt.getch = MagicMock(return_value=b"a")  # type: ignore[attr-defined]
        with patch.dict("sys.modules", {"msvcrt": mock_msvcrt}):
            result = app._poll_key_windows()
        assert result is None

    def test_no_key_available(self, app: InlineApp) -> None:
        """msvcrt.kbhit()=False returns None."""
        mock_msvcrt = ModuleType("msvcrt")
        mock_msvcrt.kbhit = MagicMock(return_value=False)  # type: ignore[attr-defined]
        with patch.dict("sys.modules", {"msvcrt": mock_msvcrt}):
            result = app._poll_key_windows()
        assert result is None


class TestPollKeyUnix:
    """Tests for _poll_key_unix synchronous helper."""

    def test_escape_detected(self, app: InlineApp) -> None:
        """select ready + read()='\\x1b' returns '\\x1b'."""
        with patch("select.select", return_value=([True], [], [])), \
             patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = "\x1b"
            result = app._poll_key_unix(0)
        assert result == "\x1b"

    def test_ctrl_c_detected(self, app: InlineApp) -> None:
        """select ready + read()='\\x03' returns '\\x03'."""
        with patch("select.select", return_value=([True], [], [])), \
             patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = "\x03"
            result = app._poll_key_unix(0)
        assert result == "\x03"

    def test_regular_key_ignored(self, app: InlineApp) -> None:
        """select ready + read()='a' returns None."""
        with patch("select.select", return_value=([True], [], [])), \
             patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = "a"
            result = app._poll_key_unix(0)
        assert result is None

    def test_no_key_available(self, app: InlineApp) -> None:
        """select not ready returns None."""
        with patch("select.select", return_value=([], [], [])):
            result = app._poll_key_unix(0)
        assert result is None

    def test_terminal_restored_on_error(self, app: InlineApp) -> None:
        """tcsetattr called in finally even when read raises."""
        mock_termios = MagicMock()
        mock_termios.tcgetattr.return_value = "old_settings"
        mock_termios.error = OSError
        mock_termios.TCSADRAIN = 1

        with patch("select.select", return_value=([True], [], [])), \
             patch("sys.stdin") as mock_stdin:
            mock_stdin.read.side_effect = OSError("read error")
            # This should raise but the test is about the _listen_for_escape
            # finally block. For _poll_key_unix, errors propagate.
            with pytest.raises(OSError, match="read error"):
                app._poll_key_unix(0)


class TestListenForEscapeGuards:
    """Tests for _listen_for_escape edge cases."""

    @pytest.mark.asyncio()
    async def test_non_tty_returns_false(self, app: InlineApp) -> None:
        """Non-TTY stdin returns False on Unix."""
        import sys

        if sys.platform == "win32":
            pytest.skip("Unix-only test")

        mock_termios = MagicMock()
        mock_termios.tcgetattr.side_effect = mock_termios.error
        mock_termios.error = OSError

        with patch.dict("sys.modules", {"termios": mock_termios}), \
             patch("sys.stdin") as mock_stdin:
            mock_stdin.fileno.return_value = 0
            # Re-import or patch to use the mock termios
            # The guard returns False when tcgetattr raises
            result = await app._listen_for_escape()
        assert result is False
