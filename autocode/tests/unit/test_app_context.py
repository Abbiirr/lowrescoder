"""Tests for AppContext protocol compliance.

InlineApp tests were removed at M11 cutover (autocode.inline deleted).
Only the AutoCodeApp (Textual fullscreen TUI) still satisfies the protocol
from Python-side; the Rust binary does not use AppContext.
"""

from __future__ import annotations

from pathlib import Path

from autocode.app.commands import AppContext
from autocode.config import AutoCodeConfig


class TestAppContextProtocol:
    def test_tui_app_satisfies_protocol(self, tmp_path: Path) -> None:
        """AutoCodeApp satisfies the AppContext protocol."""
        from autocode.tui.app import AutoCodeApp

        config = AutoCodeConfig()
        config.tui.session_db_path = str(tmp_path / "test.db")
        app = AutoCodeApp(config=config, project_root=tmp_path)
        assert isinstance(app, AppContext)
