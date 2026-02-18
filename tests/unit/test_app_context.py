"""Tests for AppContext protocol compliance."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from autocode.config import AutoCodeConfig
from autocode.tui.commands import AppContext


class TestAppContextProtocol:
    def test_inline_app_satisfies_protocol(self, tmp_path: Path) -> None:
        """InlineApp satisfies the AppContext protocol."""
        from autocode.inline.app import InlineApp

        config = AutoCodeConfig()
        config.tui.session_db_path = str(tmp_path / "test.db")
        app = InlineApp(config=config, project_root=tmp_path)
        assert isinstance(app, AppContext)

    def test_tui_app_satisfies_protocol(self, tmp_path: Path) -> None:
        """AutoCodeApp satisfies the AppContext protocol."""
        from autocode.tui.app import AutoCodeApp

        config = AutoCodeConfig()
        config.tui.session_db_path = str(tmp_path / "test.db")
        app = AutoCodeApp(config=config, project_root=tmp_path)
        assert isinstance(app, AppContext)

    def test_add_system_message_inline(self, tmp_path: Path) -> None:
        """InlineApp.add_system_message() calls renderer."""
        from autocode.inline.app import InlineApp

        config = AutoCodeConfig()
        config.tui.session_db_path = str(tmp_path / "test.db")
        app = InlineApp(config=config, project_root=tmp_path)
        with patch.object(app.renderer, "print_system") as mock:
            app.add_system_message("test message")
            mock.assert_called_once_with("test message")

    def test_get_assistant_messages(self, tmp_path: Path) -> None:
        """get_assistant_messages() returns messages with role='assistant'."""
        from autocode.inline.app import InlineApp

        config = AutoCodeConfig()
        config.tui.session_db_path = str(tmp_path / "test.db")
        app = InlineApp(config=config, project_root=tmp_path)
        # Add messages to session
        app.session_store.add_message(app.session_id, "user", "hello")
        app.session_store.add_message(app.session_id, "assistant", "hi there")
        app.session_store.add_message(app.session_id, "user", "how are you?")
        app.session_store.add_message(app.session_id, "assistant", "good thanks")
        msgs = app.get_assistant_messages()
        assert len(msgs) == 2
        assert msgs[0] == "hi there"
        assert msgs[1] == "good thanks"
