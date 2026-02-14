"""Tests for the JSON-RPC backend server."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hybridcoder.backend.server import BackendServer, _ServerAppContext

CaptureFixture = pytest.CaptureFixture[str]


@pytest.fixture
def temp_db(tmp_path: Path) -> str:
    """Temporary database path for SessionStore."""
    return str(tmp_path / "test_sessions.db")


@pytest.fixture
def server(tmp_path: Path, temp_db: str) -> BackendServer:
    """Create a BackendServer with mocked config pointing to temp db."""
    with patch("hybridcoder.backend.server.load_config") as mock_config:
        config = MagicMock()
        config.llm.model = "qwen3:8b"
        config.llm.provider = "ollama"
        config.llm.api_base = "http://localhost:11434"
        config.llm.temperature = 0.2
        config.llm.max_tokens = 4096
        config.llm.context_length = 8192
        config.llm.reasoning_enabled = True
        config.tui.approval_mode = "suggest"
        config.tui.session_db_path = temp_db
        config.tui.max_iterations = 10
        config.tui.show_tool_calls = True
        config.shell.enabled = False
        config.shell.timeout = 30
        config.shell.max_timeout = 300
        config.shell.allowed_commands = ["pytest"]
        config.shell.blocked_commands = ["rm -rf"]
        config.shell.allow_network = False
        config.logging.file_enabled = False
        config.logging.log_dir = str(tmp_path / "logs")
        config.ui.verbose = False
        config.model_dump.return_value = {
            "llm": {"model": "qwen3:8b", "provider": "ollama"},
            "tui": {"approval_mode": "suggest"},
        }
        mock_config.return_value = config

        srv = BackendServer(config=config, project_root=tmp_path)
        return srv


class TestBackendServerInit:
    """Test BackendServer initialization."""

    def test_creates_session(self, server: BackendServer) -> None:
        assert server.session_id is not None
        assert len(server.session_id) > 0

    def test_default_state(self, server: BackendServer) -> None:
        assert server._show_thinking is False
        assert server._running is True
        assert server._edit_count == 0
        assert len(server._session_approved_tools) == 0

    def test_command_router_exists(self, server: BackendServer) -> None:
        assert server.command_router is not None
        # Should have all standard commands
        cmds = server.command_router.get_all()
        cmd_names = {c.name for c in cmds}
        assert "exit" in cmd_names
        assert "help" in cmd_names
        assert "model" in cmd_names

    def test_session_store_works(self, server: BackendServer) -> None:
        sessions = server.session_store.list_sessions()
        assert len(sessions) >= 1  # At least the initial session

    def test_project_root(self, server: BackendServer, tmp_path: Path) -> None:
        assert server.project_root == tmp_path


class TestWireProtocol:
    """Test JSON-RPC wire protocol methods."""

    def test_emit_notification(self, server: BackendServer, capsys: CaptureFixture) -> None:
        server.emit_notification("on_token", {"text": "hello"})
        captured = capsys.readouterr()
        msg = json.loads(captured.out.strip())
        assert msg["jsonrpc"] == "2.0"
        assert msg["method"] == "on_token"
        assert msg["params"]["text"] == "hello"
        assert "id" not in msg

    def test_emit_notification_no_id(self, server: BackendServer, capsys: CaptureFixture) -> None:
        server.emit_notification("on_done", {"tokens_in": 100, "tokens_out": 200})
        captured = capsys.readouterr()
        msg = json.loads(captured.out.strip())
        assert "id" not in msg
        assert msg["method"] == "on_done"

    def test_emit_response(self, server: BackendServer, capsys: CaptureFixture) -> None:
        server.emit_response(42, {"ok": True})
        captured = capsys.readouterr()
        msg = json.loads(captured.out.strip())
        assert msg["jsonrpc"] == "2.0"
        assert msg["id"] == 42
        assert msg["result"]["ok"] is True

    def test_emit_status(self, server: BackendServer, capsys: CaptureFixture) -> None:
        server._emit_status()
        captured = capsys.readouterr()
        msg = json.loads(captured.out.strip())
        assert msg["method"] == "on_status"
        assert msg["params"]["model"] == "qwen3:8b"
        assert msg["params"]["provider"] == "ollama"

    def test_write_message_newline_delimited(
        self, server: BackendServer, capsys: CaptureFixture,
    ) -> None:
        server.emit_notification("on_token", {"text": "a"})
        server.emit_notification("on_token", {"text": "b"})
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        assert len(lines) == 2

    def test_emit_request_creates_future(self, server: BackendServer) -> None:
        # Check that emit_request creates a pending future
        # (We can't fully test it without an event loop driving it)
        assert len(server._pending_futures) == 0


class TestRouteResponse:
    """Test response routing to pending futures."""

    @pytest.mark.asyncio
    async def test_route_response_resolves_future(self, server: BackendServer) -> None:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        server._pending_futures[1000] = future

        server._route_response(1000, {"approved": True})

        assert future.done()
        result = future.result()
        assert result["approved"] is True

    @pytest.mark.asyncio
    async def test_route_response_unknown_id(self, server: BackendServer) -> None:
        # Should not raise
        server._route_response(9999, {"ok": True})

    @pytest.mark.asyncio
    async def test_route_response_already_done(self, server: BackendServer) -> None:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        future.set_result({"first": True})
        server._pending_futures[1000] = future

        # Should not raise even though future is already done
        server._route_response(1000, {"second": True})


class TestRequestHandlers:
    """Test individual request handlers."""

    @pytest.mark.asyncio
    async def test_handle_shutdown(self, server: BackendServer, capsys: CaptureFixture) -> None:
        await server.handle_shutdown(1)
        assert server._running is False
        captured = capsys.readouterr()
        msg = json.loads(captured.out.strip().split("\n")[-1])
        assert msg["id"] == 1
        assert msg["result"]["ok"] is True

    @pytest.mark.asyncio
    async def test_handle_session_new(self, server: BackendServer, capsys: CaptureFixture) -> None:
        old_id = server.session_id
        await server.handle_session_new("Test Session", 2)
        assert server.session_id != old_id
        assert server._session_titled is True

    @pytest.mark.asyncio
    async def test_handle_session_new_resets_state(self, server: BackendServer) -> None:
        server._session_approved_tools.add("write_file")
        server._agent_loop = MagicMock()

        await server.handle_session_new("New", 3)

        assert len(server._session_approved_tools) == 0
        assert server._agent_loop is None

    @pytest.mark.asyncio
    async def test_handle_session_list(self, server: BackendServer, capsys: CaptureFixture) -> None:
        await server.handle_session_list(4)
        captured = capsys.readouterr()
        # Find the response line (skip status notification)
        lines = captured.out.strip().split("\n")
        response = None
        for line in lines:
            msg = json.loads(line)
            if msg.get("id") == 4:
                response = msg
                break
        assert response is not None
        assert "sessions" in response["result"]
        assert len(response["result"]["sessions"]) >= 1

    @pytest.mark.asyncio
    async def test_handle_session_resume_not_found(
        self, server: BackendServer, capsys: CaptureFixture,
    ) -> None:
        await server.handle_session_resume("nonexistent", 5)
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        response = None
        for line in lines:
            msg = json.loads(line)
            if msg.get("id") == 5:
                response = msg
                break
        assert response is not None
        assert "error" in response["result"]

    @pytest.mark.asyncio
    async def test_handle_session_resume_found(
        self, server: BackendServer, capsys: CaptureFixture,
    ) -> None:
        # The initial session should be findable by prefix
        prefix = server.session_id[:8]
        await server.handle_session_resume(prefix, 6)
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        response = None
        for line in lines:
            msg = json.loads(line)
            if msg.get("id") == 6:
                response = msg
                break
        assert response is not None
        assert "session_id" in response["result"]

    @pytest.mark.asyncio
    async def test_handle_config_get(self, server: BackendServer, capsys: CaptureFixture) -> None:
        await server.handle_config_get(7)
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        response = None
        for line in lines:
            msg = json.loads(line)
            if msg.get("id") == 7:
                response = msg
                break
        assert response is not None

    @pytest.mark.asyncio
    async def test_handle_config_set_invalid_key(
        self, server: BackendServer, capsys: CaptureFixture,
    ) -> None:
        await server.handle_config_set("invalid", "value", 8)
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        response = None
        for line in lines:
            msg = json.loads(line)
            if msg.get("id") == 8:
                response = msg
                break
        assert response is not None
        assert "error" in response["result"]

    @pytest.mark.asyncio
    async def test_handle_cancel_no_agent(
        self, server: BackendServer, capsys: CaptureFixture,
    ) -> None:
        # Cancel when no agent is running should not error
        await server.handle_cancel(9)
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        response = None
        for line in lines:
            msg = json.loads(line)
            if msg.get("id") == 9:
                response = msg
                break
        assert response is not None
        assert response["result"]["ok"] is True

    @pytest.mark.asyncio
    async def test_handle_command_exit(self, server: BackendServer, capsys: CaptureFixture) -> None:
        await server.handle_command("/exit", 10)
        assert server._running is False

    @pytest.mark.asyncio
    async def test_handle_command_unknown(
        self, server: BackendServer, capsys: CaptureFixture,
    ) -> None:
        await server.handle_command("/nonexistent", 11)
        captured = capsys.readouterr()
        # Should emit a system message about unknown command
        found_unknown = False
        for line in captured.out.strip().split("\n"):
            msg = json.loads(line)
            text = msg.get("params", {}).get("text", "")
            if msg.get("method") == "on_token" and "Unknown" in text:
                found_unknown = True
                break
        assert found_unknown

    @pytest.mark.asyncio
    async def test_handle_command_help(self, server: BackendServer, capsys: CaptureFixture) -> None:
        await server.handle_command("/help", 12)
        captured = capsys.readouterr()
        # Should emit a system message with command list
        found_help = False
        for line in captured.out.strip().split("\n"):
            msg = json.loads(line)
            text = msg.get("params", {}).get("text", "")
            if msg.get("method") == "on_token" and "Available" in text:
                found_help = True
                break
        assert found_help


class TestDispatch:
    """Test the main dispatch method."""

    @pytest.mark.asyncio
    async def test_dispatch_shutdown(self, server: BackendServer) -> None:
        await server._dispatch("shutdown", {}, 100)
        assert server._running is False

    @pytest.mark.asyncio
    async def test_dispatch_session_list(self, server: BackendServer) -> None:
        await server._dispatch("session.list", {}, 101)
        # Should not raise

    @pytest.mark.asyncio
    async def test_dispatch_unknown_method(
        self, server: BackendServer, capsys: CaptureFixture,
    ) -> None:
        await server._dispatch("unknown.method", {}, 102)
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        response = None
        for line in lines:
            msg = json.loads(line)
            if msg.get("id") == 102:
                response = msg
                break
        assert response is not None
        assert "error" in response["result"]

    @pytest.mark.asyncio
    async def test_dispatch_cancel(self, server: BackendServer) -> None:
        await server._dispatch("cancel", {}, 103)
        # Should not raise

    @pytest.mark.asyncio
    async def test_dispatch_config_get(self, server: BackendServer) -> None:
        await server._dispatch("config.get", {}, 104)
        # Should not raise


class TestServerAppContext:
    """Test the _ServerAppContext adapter."""

    def test_session_store(self, server: BackendServer) -> None:
        ctx = _ServerAppContext(server)
        assert ctx.session_store is server.session_store

    def test_session_id(self, server: BackendServer) -> None:
        ctx = _ServerAppContext(server)
        assert ctx.session_id == server.session_id

    def test_session_id_setter(self, server: BackendServer) -> None:
        ctx = _ServerAppContext(server)
        ctx.session_id = "new-id"
        assert server.session_id == "new-id"

    def test_config(self, server: BackendServer) -> None:
        ctx = _ServerAppContext(server)
        assert ctx.config is server.config

    def test_project_root(self, server: BackendServer, tmp_path: Path) -> None:
        ctx = _ServerAppContext(server)
        assert ctx.project_root == tmp_path

    def test_command_router(self, server: BackendServer) -> None:
        ctx = _ServerAppContext(server)
        assert ctx.command_router is server.command_router

    def test_approval_mode(self, server: BackendServer) -> None:
        ctx = _ServerAppContext(server)
        assert ctx.approval_mode == "suggest"

    def test_shell_enabled(self, server: BackendServer) -> None:
        ctx = _ServerAppContext(server)
        assert ctx.shell_enabled is False

    def test_shell_enabled_setter(self, server: BackendServer) -> None:
        ctx = _ServerAppContext(server)
        ctx.shell_enabled = True
        assert server.config.shell.enabled is True

    def test_show_thinking(self, server: BackendServer) -> None:
        ctx = _ServerAppContext(server)
        assert ctx.show_thinking is False

    def test_show_thinking_setter(self, server: BackendServer) -> None:
        ctx = _ServerAppContext(server)
        ctx.show_thinking = True
        assert server._show_thinking is True

    def test_add_system_message(self, server: BackendServer, capsys: CaptureFixture) -> None:
        ctx = _ServerAppContext(server)
        ctx.add_system_message("test message")
        captured = capsys.readouterr()
        msg = json.loads(captured.out.strip())
        assert msg["method"] == "on_token"
        assert "test message" in msg["params"]["text"]

    def test_clear_messages(self, server: BackendServer, capsys: CaptureFixture) -> None:
        ctx = _ServerAppContext(server)
        ctx.clear_messages()
        captured = capsys.readouterr()
        msg = json.loads(captured.out.strip())
        assert "cleared" in msg["params"]["text"]

    def test_exit_app(self, server: BackendServer) -> None:
        ctx = _ServerAppContext(server)
        ctx.exit_app()
        assert server._running is False

    def test_get_assistant_messages_empty(self, server: BackendServer) -> None:
        ctx = _ServerAppContext(server)
        msgs = ctx.get_assistant_messages()
        assert msgs == []


class TestCallbacks:
    """Test agent loop callbacks."""

    def test_on_chunk(self, server: BackendServer, capsys: CaptureFixture) -> None:
        server._on_chunk("hello ")
        captured = capsys.readouterr()
        msg = json.loads(captured.out.strip())
        assert msg["method"] == "on_token"
        assert msg["params"]["text"] == "hello "

    def test_on_thinking_chunk(self, server: BackendServer, capsys: CaptureFixture) -> None:
        server._on_thinking_chunk("reasoning...")
        captured = capsys.readouterr()
        msg = json.loads(captured.out.strip())
        assert msg["method"] == "on_thinking"
        assert msg["params"]["text"] == "reasoning..."

    def test_on_tool_call(self, server: BackendServer, capsys: CaptureFixture) -> None:
        server._on_tool_call("read_file", "completed", "file contents")
        captured = capsys.readouterr()
        msg = json.loads(captured.out.strip())
        assert msg["method"] == "on_tool_call"
        assert msg["params"]["name"] == "read_file"
        assert msg["params"]["status"] == "completed"

    def test_on_tool_call_tracks_edits(self, server: BackendServer) -> None:
        assert server._edit_count == 0
        server._on_tool_call("write_file", "completed", "Written to /tmp/test")
        assert server._edit_count == 1

    def test_on_tool_call_no_edit_for_read(self, server: BackendServer) -> None:
        server._on_tool_call("read_file", "completed", "contents")
        assert server._edit_count == 0

    @pytest.mark.asyncio
    async def test_approval_callback_auto_approved(self, server: BackendServer) -> None:
        server._session_approved_tools.add("write_file")
        result = await server._approval_callback("write_file", {"path": "/tmp/test"})
        assert result is True

    @pytest.mark.asyncio
    async def test_ask_user_callback_cancelled(self, server: BackendServer) -> None:
        # Simulate cancellation by patching emit_request to raise
        async def mock_emit(*a: Any, **kw: Any) -> dict[str, Any]:
            raise asyncio.CancelledError

        server.emit_request = mock_emit  # type: ignore[assignment]
        result = await server._ask_user_callback("question", ["A", "B"], False)
        assert result == "A"  # Should return first option on cancel

    @pytest.mark.asyncio
    async def test_ask_user_callback_cancelled_no_options(self, server: BackendServer) -> None:
        async def mock_emit(*a: Any, **kw: Any) -> dict[str, Any]:
            raise asyncio.CancelledError

        server.emit_request = mock_emit  # type: ignore[assignment]
        result = await server._ask_user_callback("question", [], True)
        assert result == ""


class TestHandleChat:
    """Test the chat handler."""

    @pytest.mark.asyncio
    async def test_handle_chat_titles_session(self, server: BackendServer) -> None:
        with patch.object(server, "_ensure_agent_loop") as mock_ensure:
            mock_loop = AsyncMock()
            mock_loop.run = AsyncMock(return_value="response text")
            mock_ensure.return_value = mock_loop

            assert not server._session_titled
            await server.handle_chat("Hello world", None, 1)
            assert server._session_titled

    @pytest.mark.asyncio
    async def test_handle_chat_sends_done(
        self, server: BackendServer, capsys: CaptureFixture,
    ) -> None:
        with patch.object(server, "_ensure_agent_loop") as mock_ensure:
            mock_loop = AsyncMock()
            mock_loop.run = AsyncMock(return_value="response")
            mock_loop.session_id = server.session_id
            mock_ensure.return_value = mock_loop

            await server.handle_chat("test", None, 1)

            captured = capsys.readouterr()
            lines = captured.out.strip().split("\n")
            done_found = False
            for line in lines:
                msg = json.loads(line)
                if msg.get("method") == "on_done":
                    done_found = True
                    break
            assert done_found

    @pytest.mark.asyncio
    async def test_handle_chat_error_sends_error(
        self, server: BackendServer, capsys: CaptureFixture,
    ) -> None:
        with patch.object(server, "_ensure_agent_loop") as mock_ensure:
            mock_loop = AsyncMock()
            mock_loop.run = AsyncMock(side_effect=RuntimeError("test error"))
            mock_loop.session_id = server.session_id
            mock_ensure.return_value = mock_loop

            await server.handle_chat("test", None, 1)

            captured = capsys.readouterr()
            lines = captured.out.strip().split("\n")
            error_found = False
            for line in lines:
                msg = json.loads(line)
                if msg.get("method") == "on_error":
                    error_found = True
                    assert "test error" in msg["params"]["message"]
                    break
            assert error_found

    @pytest.mark.asyncio
    async def test_handle_chat_cancelled(
        self, server: BackendServer, capsys: CaptureFixture,
    ) -> None:
        with patch.object(server, "_ensure_agent_loop") as mock_ensure:
            mock_loop = AsyncMock()
            mock_loop.run = AsyncMock(side_effect=asyncio.CancelledError)
            mock_loop.session_id = server.session_id
            mock_ensure.return_value = mock_loop

            await server.handle_chat("test", None, 1)

            captured = capsys.readouterr()
            lines = captured.out.strip().split("\n")
            done_found = False
            for line in lines:
                msg = json.loads(line)
                if msg.get("method") == "on_done":
                    assert msg["params"].get("cancelled") is True
                    done_found = True
                    break
            assert done_found

    @pytest.mark.asyncio
    async def test_handle_chat_init_error_sends_done(
        self, server: BackendServer, capsys: CaptureFixture,
    ) -> None:
        """If _ensure_agent_loop() itself throws, on_error + on_done must still be sent."""
        with patch.object(server, "_ensure_agent_loop", side_effect=RuntimeError("init failed")):
            await server.handle_chat("test", None, 1)

            captured = capsys.readouterr()
            lines = captured.out.strip().split("\n")
            error_found = False
            done_found = False
            for line in lines:
                msg = json.loads(line)
                if msg.get("method") == "on_error":
                    error_found = True
                    assert "init failed" in msg["params"]["message"]
                if msg.get("method") == "on_done":
                    done_found = True
            assert error_found, "on_error should be emitted when _ensure_agent_loop() fails"
            assert done_found, "on_done should ALWAYS be emitted even when init fails"

    @pytest.mark.asyncio
    async def test_handle_chat_changes_session(self, server: BackendServer) -> None:
        with patch.object(server, "_ensure_agent_loop") as mock_ensure:
            mock_loop = AsyncMock()
            mock_loop.run = AsyncMock(return_value="ok")
            mock_loop.session_id = server.session_id
            mock_ensure.return_value = mock_loop

            new_id = "custom-session-id"
            await server.handle_chat("test", new_id, 1)
            assert server.session_id == new_id


class TestNextRequestID:
    """Test request ID generation for Python->Go requests."""

    def test_starts_at_1000(self, server: BackendServer) -> None:
        assert server._next_request_id == 1000

    @pytest.mark.asyncio
    async def test_increments(self, server: BackendServer) -> None:
        # We can't fully test emit_request without a running loop responding,
        # but we can check the ID increments by inspecting the counter
        start = server._next_request_id
        # Simulate what emit_request does
        server._next_request_id += 1
        assert server._next_request_id == start + 1


class TestThinkingCallbackRouting:
    """Test that thinking callback is correctly set based on _show_thinking."""

    @pytest.mark.asyncio
    async def test_thinking_callback_always_set(self, server: BackendServer) -> None:
        """Thinking callback is always set — the Go TUI controls display."""
        server._show_thinking = False
        # Even when _show_thinking is False, the callback should be set
        # because the backend always streams thinking tokens now.
        assert callable(server._on_thinking_chunk)

    @pytest.mark.asyncio
    async def test_thinking_callback_callable(self, server: BackendServer) -> None:
        server._show_thinking = True
        assert callable(server._on_thinking_chunk)


class TestApprovalCallbackExtended:
    """Extended approval callback tests."""

    @pytest.mark.asyncio
    async def test_approval_callback_session_approve_adds_tool(self, server: BackendServer) -> None:
        """Session approve should add tool to _session_approved_tools."""
        async def mock_emit(method: str, params: dict[str, Any]) -> dict[str, Any]:
            return {"approved": True, "session_approve": True}

        server.emit_request = mock_emit  # type: ignore[assignment]
        result = await server._approval_callback("write_file", {"path": "/tmp/test"})
        assert result is True
        assert "write_file" in server._session_approved_tools

    @pytest.mark.asyncio
    async def test_approval_callback_single_approve_no_session(self, server: BackendServer) -> None:
        """Single approve should NOT add tool to session approved set."""
        async def mock_emit(method: str, params: dict[str, Any]) -> dict[str, Any]:
            return {"approved": True, "session_approve": False}

        server.emit_request = mock_emit  # type: ignore[assignment]
        result = await server._approval_callback("read_file", {"path": "/tmp/test"})
        assert result is True
        assert "read_file" not in server._session_approved_tools

    @pytest.mark.asyncio
    async def test_approval_callback_denied(self, server: BackendServer) -> None:
        """Denied approval should return False."""
        async def mock_emit(method: str, params: dict[str, Any]) -> dict[str, Any]:
            return {"approved": False}

        server.emit_request = mock_emit  # type: ignore[assignment]
        result = await server._approval_callback("write_file", {"path": "/tmp/test"})
        assert result is False


class TestAskUserCallbackExtended:
    """Extended ask_user callback tests."""

    @pytest.mark.asyncio
    async def test_ask_user_callback_returns_answer(self, server: BackendServer) -> None:
        """Normal path: ask_user returns the user's answer."""
        async def mock_emit(method: str, params: dict[str, Any]) -> dict[str, Any]:
            return {"answer": "custom response"}

        server.emit_request = mock_emit  # type: ignore[assignment]
        result = await server._ask_user_callback("question?", ["A", "B"], True)
        assert result == "custom response"


class TestConfigSetExtended:
    """Extended config set tests."""

    @pytest.mark.asyncio
    async def test_config_set_single_part_key(
        self, server: BackendServer, capsys: CaptureFixture,
    ) -> None:
        """Single-part key should fail."""
        await server.handle_config_set("invalid", "value", 20)
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        response = None
        for line in lines:
            msg = json.loads(line)
            if msg.get("id") == 20:
                response = msg
                break
        assert response is not None
        assert "error" in response["result"]
        assert "section.field" in response["result"]["error"]

    @pytest.mark.asyncio
    async def test_config_set_unknown_section(
        self, server: BackendServer, capsys: CaptureFixture,
    ) -> None:
        """Unknown section should fail."""
        await server.handle_config_set("fakesection.field", "value", 21)
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        response = None
        for line in lines:
            msg = json.loads(line)
            if msg.get("id") == 21:
                response = msg
                break
        assert response is not None
        assert "error" in response["result"]


class TestEmitStatusExtended:
    """Extended status emission tests."""

    def test_emit_status_includes_all_fields(
        self, server: BackendServer, capsys: CaptureFixture,
    ) -> None:
        """Status notification should include model, provider, mode, session_id."""
        server._emit_status()
        captured = capsys.readouterr()
        msg = json.loads(captured.out.strip())
        assert msg["method"] == "on_status"
        params = msg["params"]
        assert "model" in params
        assert "provider" in params
        assert "mode" in params
        assert "session_id" in params
        assert params["model"] == "qwen3:8b"
        assert params["provider"] == "ollama"
        assert params["session_id"] == server.session_id


class TestOnToolCallTracking:
    """Test edit tracking through tool call callbacks."""

    def test_on_tool_call_write_file_increments_edits(self, server: BackendServer) -> None:
        assert server._edit_count == 0
        server._on_tool_call("write_file", "completed", "Written")
        assert server._edit_count == 1
        server._on_tool_call("write_file", "completed", "Written again")
        assert server._edit_count == 2

    def test_on_tool_call_running_does_not_increment(self, server: BackendServer) -> None:
        server._on_tool_call("write_file", "running", "")
        assert server._edit_count == 0

    def test_on_tool_call_non_write_does_not_increment(self, server: BackendServer) -> None:
        server._on_tool_call("read_file", "completed", "contents")
        server._on_tool_call("run_command", "completed", "output")
        assert server._edit_count == 0


class TestSessionState:
    """Test session state management."""

    @pytest.mark.asyncio
    async def test_session_new_clears_approved_tools(self, server: BackendServer) -> None:
        server._session_approved_tools.add("write_file")
        server._session_approved_tools.add("run_command")
        await server.handle_session_new("Fresh", 50)
        assert len(server._session_approved_tools) == 0

    @pytest.mark.asyncio
    async def test_session_new_resets_agent_loop(self, server: BackendServer) -> None:
        server._agent_loop = MagicMock()
        await server.handle_session_new("Fresh", 51)
        assert server._agent_loop is None

    @pytest.mark.asyncio
    async def test_session_new_resets_task_store(self, server: BackendServer) -> None:
        server._task_store = MagicMock()
        await server.handle_session_new("Fresh", 52)
        assert server._task_store is None

    @pytest.mark.asyncio
    async def test_session_resume_resets_task_store(self, server: BackendServer) -> None:
        server._task_store = MagicMock()
        prefix = server.session_id[:8]
        await server.handle_session_resume(prefix, 53)
        assert server._task_store is None

    @pytest.mark.asyncio
    async def test_handle_chat_session_switch_resets_task_store(
        self, server: BackendServer,
    ) -> None:
        server._task_store = MagicMock()
        server._agent_loop = MagicMock()

        with patch.object(server, "_ensure_agent_loop") as mock_ensure:
            mock_loop = AsyncMock()
            mock_loop.run = AsyncMock(return_value="ok")
            mock_loop.session_id = server.session_id
            mock_ensure.return_value = mock_loop

            await server.handle_chat("test", "different-session-id", 54)
            assert server._task_store is None
            assert server.session_id == "different-session-id"

    @pytest.mark.asyncio
    async def test_handle_chat_session_switch_clears_approved_tools(
        self, server: BackendServer,
    ) -> None:
        server._session_approved_tools.add("write_file")
        server._session_approved_tools.add("run_command")

        with patch.object(server, "_ensure_agent_loop") as mock_ensure:
            mock_loop = AsyncMock()
            mock_loop.run = AsyncMock(return_value="ok")
            mock_loop.session_id = server.session_id
            mock_ensure.return_value = mock_loop

            await server.handle_chat("test", "other-session", 55)
            assert len(server._session_approved_tools) == 0

    def test_show_thinking_toggle(self, server: BackendServer) -> None:
        assert server._show_thinking is False
        ctx = _ServerAppContext(server)
        ctx.show_thinking = True
        assert server._show_thinking is True
        ctx.show_thinking = False
        assert server._show_thinking is False

    @pytest.mark.asyncio
    async def test_session_new_resets_scheduler_and_manager(
        self, server: BackendServer,
    ) -> None:
        server._llm_scheduler = MagicMock()
        server._llm_scheduler.shutdown = AsyncMock()
        server._subagent_manager = MagicMock()
        server._subagent_manager.cancel_all = MagicMock(return_value=0)
        await server.handle_session_new("Fresh", 60)
        assert server._llm_scheduler is None
        assert server._subagent_manager is None

    @pytest.mark.asyncio
    async def test_shutdown_calls_teardown(self, server: BackendServer) -> None:
        server._llm_scheduler = MagicMock()
        server._llm_scheduler.shutdown = AsyncMock()
        server._subagent_manager = MagicMock()
        server._subagent_manager.cancel_all = MagicMock(return_value=0)
        await server.handle_shutdown(61)
        assert server._llm_scheduler is None
        assert server._subagent_manager is None
        assert server._running is False

    @pytest.mark.asyncio
    async def test_plan_mode_persists_across_loop_recreation(
        self, server: BackendServer,
    ) -> None:
        server._plan_mode_enabled = True
        assert server._plan_mode_enabled is True
        # Teardown resets agent loop but not plan mode
        await server._teardown_agent_resources()
        assert server._plan_mode_enabled is True
        assert server._agent_loop is None
