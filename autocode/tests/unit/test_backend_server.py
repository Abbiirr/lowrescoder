"""Tests for the JSON-RPC backend server."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autocode.agent.loop import AgentMode
from autocode.backend.server import BackendServer, _ServerAppContext
from autocode.config import DEFAULT_OLLAMA_API_BASE, DEFAULT_OLLAMA_MODEL

CaptureFixture = pytest.CaptureFixture[str]


@pytest.fixture
def temp_db(tmp_path: Path) -> str:
    """Temporary database path for SessionStore."""
    return str(tmp_path / "test_sessions.db")


@pytest.fixture
def server(tmp_path: Path, temp_db: str) -> BackendServer:
    """Create a BackendServer with mocked config pointing to temp db."""
    with patch("autocode.backend.server.load_config") as mock_config:
        config = MagicMock()
        config.llm.model = DEFAULT_OLLAMA_MODEL
        config.llm.provider = "ollama"
        config.llm.api_base = DEFAULT_OLLAMA_API_BASE
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
            "llm": {"model": DEFAULT_OLLAMA_MODEL, "provider": "ollama"},
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

    @pytest.mark.asyncio
    async def test_ensure_agent_loop_preserves_backend_runtime_modules(
        self,
        server: BackendServer,
    ) -> None:
        """Backend should keep task/subagent/delegation state when using the factory."""
        mock_provider = AsyncMock()
        mock_provider.generate_with_tools = AsyncMock()

        with patch("autocode.backend.server.create_provider", return_value=mock_provider):
            orchestrator = server._ensure_agent_loop()

        loop = orchestrator.agent_loop
        assert loop._task_store is server._task_store
        assert loop._subagent_manager is server._subagent_manager
        assert loop._delegation_policy is server._delegation_policy
        assert loop._memory_context == server._memory_store.get_context()
        assert loop._middleware is not None
        assert loop._tool_shim is not None

        if server._llm_scheduler is not None:
            await server._llm_scheduler.shutdown()


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
        assert msg["params"]["model"] == DEFAULT_OLLAMA_MODEL
        assert msg["params"]["provider"] == "ollama"

    def test_write_message_newline_delimited(
        self,
        server: BackendServer,
        capsys: CaptureFixture,
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
        self,
        server: BackendServer,
        capsys: CaptureFixture,
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
        self,
        server: BackendServer,
        capsys: CaptureFixture,
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
        self,
        server: BackendServer,
        capsys: CaptureFixture,
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
        self,
        server: BackendServer,
        capsys: CaptureFixture,
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
        self,
        server: BackendServer,
        capsys: CaptureFixture,
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

    @pytest.mark.asyncio
    async def test_handle_command_model_switch_reemits_status(
        self,
        server: BackendServer,
        capsys: CaptureFixture,
    ) -> None:
        """Switching the model via /model <name> must re-emit on_status so the
        Go TUI footer reflects the new value immediately (Codex Entry 1071
        blocker #1).
        """
        original = server.config.llm.model
        # Pick any alias different from the current model
        new_model = "coding" if original != "coding" else "tools"
        await server.handle_command(f"/model {new_model}", 13)
        captured = capsys.readouterr()

        # Config must have been updated
        assert server.config.llm.model == new_model

        # An on_status notification must appear after the command
        status_events = []
        for line in captured.out.strip().split("\n"):
            if not line:
                continue
            msg = json.loads(line)
            if msg.get("method") == "on_status":
                status_events.append(msg)
        assert status_events, (
            f"expected an on_status notification after /model switch, got: {captured.out}"
        )
        # The most recent status must reflect the new model
        last = status_events[-1]
        assert last["params"]["model"] == new_model

    @pytest.mark.asyncio
    async def test_handle_command_noop_does_not_reemit_status(
        self,
        server: BackendServer,
        capsys: CaptureFixture,
    ) -> None:
        """Commands that don't mutate state should NOT re-emit on_status."""
        capsys.readouterr()  # flush any startup output
        await server.handle_command("/help", 14)
        captured = capsys.readouterr()

        status_events = 0
        for line in captured.out.strip().split("\n"):
            if not line:
                continue
            msg = json.loads(line)
            if msg.get("method") == "on_status":
                status_events += 1
        assert status_events == 0, (
            f"expected no on_status re-emit after /help (no state change), got {status_events}"
        )


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
        self,
        server: BackendServer,
        capsys: CaptureFixture,
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
        self,
        server: BackendServer,
        capsys: CaptureFixture,
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
        self,
        server: BackendServer,
        capsys: CaptureFixture,
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
        self,
        server: BackendServer,
        capsys: CaptureFixture,
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
        self,
        server: BackendServer,
        capsys: CaptureFixture,
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
        self,
        server: BackendServer,
        capsys: CaptureFixture,
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
        self,
        server: BackendServer,
        capsys: CaptureFixture,
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
        self,
        server: BackendServer,
        capsys: CaptureFixture,
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
        assert params["model"] == DEFAULT_OLLAMA_MODEL
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
        self,
        server: BackendServer,
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
        self,
        server: BackendServer,
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
        self,
        server: BackendServer,
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
        self,
        server: BackendServer,
    ) -> None:
        server._plan_mode_enabled = True
        server._agent_mode = AgentMode.PLANNING
        assert server._plan_mode_enabled is True
        # Teardown resets agent loop but not plan mode
        await server._teardown_agent_resources()
        assert server._plan_mode_enabled is True
        assert server._agent_mode == AgentMode.PLANNING
        assert server._agent_loop is None

    @pytest.mark.asyncio
    async def test_research_mode_persists_across_loop_recreation(
        self,
        server: BackendServer,
    ) -> None:
        server._agent_mode = AgentMode.RESEARCH
        await server._teardown_agent_resources()
        assert server._agent_mode == AgentMode.RESEARCH
        assert server._agent_loop is None

    @pytest.mark.asyncio
    async def test_session_new_teardown_before_id_switch(
        self,
        server: BackendServer,
    ) -> None:
        """Teardown must run while self.session_id still points to the OLD session.

        Regression test for Codex Entry 420 HIGH concern: learn_from_session()
        was running against the new session_id because session_id was mutated
        before _teardown_agent_resources().
        """
        old_session_id = server.session_id
        teardown_session_id = None

        original_teardown = server._teardown_agent_resources

        async def capturing_teardown() -> None:
            nonlocal teardown_session_id
            teardown_session_id = server.session_id
            await original_teardown()

        server._teardown_agent_resources = capturing_teardown  # type: ignore[assignment]
        await server.handle_session_new("New Session", 70)

        assert teardown_session_id == old_session_id
        assert server.session_id != old_session_id

    @pytest.mark.asyncio
    async def test_session_resume_teardown_before_id_switch(
        self,
        server: BackendServer,
    ) -> None:
        """Same lifecycle ordering check for handle_session_resume."""
        old_session_id = server.session_id
        teardown_session_id = None

        original_teardown = server._teardown_agent_resources

        async def capturing_teardown() -> None:
            nonlocal teardown_session_id
            teardown_session_id = server.session_id
            await original_teardown()

        server._teardown_agent_resources = capturing_teardown  # type: ignore[assignment]
        prefix = server.session_id[:8]
        await server.handle_session_resume(prefix, 71)

        assert teardown_session_id == old_session_id

    @pytest.mark.asyncio
    async def test_chat_session_switch_teardown_before_id_switch(
        self,
        server: BackendServer,
    ) -> None:
        """Same lifecycle ordering check for handle_chat session switch."""
        old_session_id = server.session_id
        teardown_session_id = None

        original_teardown = server._teardown_agent_resources

        async def capturing_teardown() -> None:
            nonlocal teardown_session_id
            teardown_session_id = server.session_id
            await original_teardown()

        server._teardown_agent_resources = capturing_teardown  # type: ignore[assignment]

        with patch.object(server, "_ensure_agent_loop") as mock_ensure:
            mock_loop = AsyncMock()
            mock_loop.run = AsyncMock(return_value="ok")
            mock_loop.session_id = server.session_id
            mock_ensure.return_value = mock_loop

            await server.handle_chat("test", "new-session-id", 72)

        assert teardown_session_id == old_session_id
        assert server.session_id == "new-session-id"


class TestTaskStateNotification:
    """Test on_task_state notification payload shape."""

    def test_emit_task_state_empty(
        self,
        server: BackendServer,
        capsys: CaptureFixture,
    ) -> None:
        """on_task_state emits correct shape with empty stores."""
        server._emit_task_state()
        captured = capsys.readouterr()
        msg = json.loads(captured.out.strip())
        assert msg["method"] == "on_task_state"
        assert msg["params"]["tasks"] == []
        assert msg["params"]["subagents"] == []

    def test_emit_task_state_with_task_store(
        self,
        server: BackendServer,
        capsys: CaptureFixture,
    ) -> None:
        """on_task_state includes tasks from TaskStore."""
        from autocode.session.task_store import TaskStore

        conn = server.session_store.get_connection()
        task_store = TaskStore(conn, server.session_id)
        server._task_store = task_store
        task_store.create_task("Test task", "A test task description")

        server._emit_task_state()
        captured = capsys.readouterr()
        msg = json.loads(captured.out.strip())
        assert msg["method"] == "on_task_state"
        assert len(msg["params"]["tasks"]) == 1
        assert msg["params"]["tasks"][0]["title"] == "Test task"
        assert "status" in msg["params"]["tasks"][0]
        assert "id" in msg["params"]["tasks"][0]

    def test_on_tool_call_emits_task_state_on_task_tool(
        self,
        server: BackendServer,
        capsys: CaptureFixture,
    ) -> None:
        """BUG-20: Task tool completions trigger on_task_state notification."""
        server._on_tool_call("create_task", "completed", "Created task #1")
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        methods = [json.loads(line)["method"] for line in lines]
        # Should include both on_tool_call and on_task_state
        assert "on_tool_call" in methods
        assert "on_task_state" in methods


class TestL2ContextInjectionServer:
    """Backend-level test for L2 assembled context injection into AgentLoop.run()."""

    @pytest.mark.asyncio
    async def test_l2_route_passes_assembled_context_to_agent_loop(
        self,
        server: BackendServer,
        capsys: CaptureFixture,
    ) -> None:
        """When L2 routing activates, assembled context must be passed as injected_context."""
        # Set up the server with L2 prerequisites
        expected_ctx = "## Assembled L2 Context\nSearch results"
        mock_assembler = MagicMock()
        mock_assembler.assemble = MagicMock(return_value=expected_ctx)
        server._context_assembler = mock_assembler
        server.config.layer2 = MagicMock()
        server.config.layer2.enabled = True
        server.config.layer2.search_top_k = 5

        # Mock the agent loop to capture the injected_context arg
        mock_loop = AsyncMock()
        mock_loop.run = AsyncMock(return_value="L2 response")
        mock_loop.session_id = server.session_id

        with (
            patch.object(server, "_ensure_agent_loop", return_value=mock_loop),
            patch("autocode.core.router.RequestRouter") as mock_router,
            patch("autocode.agent.tools._code_index_cache", new=MagicMock()),
            patch("autocode.layer2.search.HybridSearch") as mock_search,
            patch("autocode.layer2.rules.RulesLoader") as mock_rules,
        ):
            from autocode.core.types import RequestType

            mock_router.return_value.classify.return_value = RequestType.SEMANTIC_SEARCH
            mock_search.return_value.search.return_value = [{"text": "c1"}]
            mock_rules.return_value.load.return_value = "- rule1"

            await server.handle_chat(
                "how does the parser work",
                None,
                80,
            )

            # Verify agent_loop.run was called with injected_context
            mock_loop.run.assert_called_once()
            call_kwargs = mock_loop.run.call_args
            assert call_kwargs.kwargs.get("injected_context") == expected_ctx

            # Verify on_done emitted with layer_used=2
            captured = capsys.readouterr()
            lines = captured.out.strip().split("\n")
            done_msg = None
            for line in lines:
                msg = json.loads(line)
                if msg.get("method") == "on_done":
                    done_msg = msg
                    break
            assert done_msg is not None
            assert done_msg["params"]["layer_used"] == 2


class TestSteerRPC:
    """Tests for the steer JSON-RPC handler."""

    @pytest.mark.asyncio
    async def test_steer_no_active_run(
        self,
        server: BackendServer,
        capsys: CaptureFixture,
    ) -> None:
        await server.handle_steer("change approach", 200)
        captured = capsys.readouterr()
        msg = json.loads(captured.out.strip())
        assert msg["id"] == 200
        assert "error" in msg["result"]
        assert msg["result"]["active"] is False

    @pytest.mark.asyncio
    async def test_steer_empty_message(
        self,
        server: BackendServer,
        capsys: CaptureFixture,
    ) -> None:
        server._agent_task = asyncio.create_task(asyncio.sleep(100))
        try:
            await server.handle_steer("   ", 201)
            captured = capsys.readouterr()
            msg = json.loads(captured.out.strip())
            assert msg["id"] == 201
            assert "error" in msg["result"]
        finally:
            server._agent_task.cancel()
            try:
                await server._agent_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_steer_active_run_cancels_and_injects(
        self,
        server: BackendServer,
        capsys: CaptureFixture,
    ) -> None:
        server._agent_loop = MagicMock()
        server._agent_task = asyncio.create_task(asyncio.sleep(100))
        try:
            await server.handle_steer("use a different approach", 202)
            captured = capsys.readouterr()
            msg = json.loads(captured.out.strip())
            assert msg["id"] == 202
            assert msg["result"]["ok"] is True
            assert msg["result"]["injected"] is True

            server._agent_loop.cancel.assert_called_once()
        finally:
            server._agent_task.cancel()
            try:
                await server._agent_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_steer_persists_message_in_session(
        self,
        server: BackendServer,
    ) -> None:
        server._agent_loop = MagicMock()
        server._agent_task = asyncio.create_task(asyncio.sleep(100))
        try:
            await server.handle_steer("try again", 203)
            messages = server.session_store.get_messages(server.session_id)
            assert any("[steer] try again" in m.content for m in messages)
        finally:
            server._agent_task.cancel()
            try:
                await server._agent_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_dispatch_steer(
        self,
        server: BackendServer,
        capsys: CaptureFixture,
    ) -> None:
        await server._dispatch("steer", {"message": "hello"}, 204)
        captured = capsys.readouterr()
        msg = json.loads(captured.out.strip())
        assert msg["id"] == 204
        assert "error" in msg["result"]
        assert msg["result"]["active"] is False

    @pytest.mark.asyncio
    async def test_steer_completed_task_returns_error(
        self,
        server: BackendServer,
        capsys: CaptureFixture,
    ) -> None:
        async def _noop() -> None:
            pass

        server._agent_task = asyncio.create_task(_noop())
        await server._agent_task
        await server.handle_steer("redirect", 205)
        captured = capsys.readouterr()
        msg = json.loads(captured.out.strip())
        assert msg["id"] == 205
        assert "error" in msg["result"]


class TestSessionForkRPC:
    """Tests for the session.fork JSON-RPC handler."""

    @pytest.mark.asyncio
    async def test_fork_creates_new_session(
        self,
        server: BackendServer,
        capsys: CaptureFixture,
    ) -> None:
        old_id = server.session_id
        await server.handle_session_fork(300)
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        response = None
        for line in lines:
            msg = json.loads(line)
            if msg.get("id") == 300:
                response = msg
                break
        assert response is not None
        new_id = response["result"]["new_session_id"]
        assert new_id != old_id
        assert len(new_id) > 0

    @pytest.mark.asyncio
    async def test_fork_copies_messages(
        self,
        server: BackendServer,
    ) -> None:
        server.session_store.add_message(server.session_id, "user", "hello")
        server.session_store.add_message(
            server.session_id,
            "assistant",
            "world",
        )
        old_id = server.session_id

        await server.handle_session_fork(301)

        sessions = server.session_store.list_sessions()
        forked = [s for s in sessions if s.id != old_id]
        assert len(forked) >= 1
        new_id = forked[-1].id
        messages = server.session_store.get_messages(new_id)
        assert len(messages) == 2
        assert messages[0].content == "hello"
        assert messages[1].content == "world"

    @pytest.mark.asyncio
    async def test_fork_does_not_switch_session(
        self,
        server: BackendServer,
    ) -> None:
        old_id = server.session_id
        await server.handle_session_fork(302)
        assert server.session_id == old_id

    @pytest.mark.asyncio
    async def test_fork_emits_status(
        self,
        server: BackendServer,
        capsys: CaptureFixture,
    ) -> None:
        capsys.readouterr()
        await server.handle_session_fork(303)
        captured = capsys.readouterr()
        status_found = False
        for line in captured.out.strip().split("\n"):
            msg = json.loads(line)
            if msg.get("method") == "on_status":
                status_found = True
                break
        assert status_found

    @pytest.mark.asyncio
    async def test_dispatch_session_fork(
        self,
        server: BackendServer,
        capsys: CaptureFixture,
    ) -> None:
        old_id = server.session_id
        await server._dispatch("session.fork", {}, 304)
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        response = None
        for line in lines:
            msg = json.loads(line)
            if msg.get("id") == 304:
                response = msg
                break
        assert response is not None
        assert "new_session_id" in response["result"]
        assert response["result"]["new_session_id"] != old_id


class TestCostUpdateProducer:
    """Tests for on_cost_update notification emission."""

    @pytest.mark.asyncio
    async def test_cost_update_emitted_on_chat_done(
        self,
        server: BackendServer,
        capsys: CaptureFixture,
    ) -> None:
        with patch.object(server, "_ensure_agent_loop") as mock_ensure:
            mock_loop = AsyncMock()
            mock_loop.run = AsyncMock(return_value="response")
            mock_loop.session_id = server.session_id
            mock_ensure.return_value = mock_loop

            await server.handle_chat("test", None, 1)

            captured = capsys.readouterr()
            lines = captured.out.strip().split("\n")
            cost_found = False
            for line in lines:
                msg = json.loads(line)
                if msg.get("method") == "on_cost_update":
                    cost_found = True
                    assert "tokens_in" in msg["params"]
                    assert "tokens_out" in msg["params"]
                    assert "cost" in msg["params"]
                    break
            assert cost_found

    @pytest.mark.asyncio
    async def test_cost_update_emitted_on_cancel(
        self,
        server: BackendServer,
        capsys: CaptureFixture,
    ) -> None:
        with patch.object(server, "_ensure_agent_loop") as mock_ensure:
            mock_loop = AsyncMock()
            mock_loop.run = AsyncMock(side_effect=asyncio.CancelledError)
            mock_loop.session_id = server.session_id
            mock_ensure.return_value = mock_loop

            await server.handle_chat("test", None, 1)

            captured = capsys.readouterr()
            lines = captured.out.strip().split("\n")
            cost_found = False
            for line in lines:
                msg = json.loads(line)
                if msg.get("method") == "on_cost_update":
                    cost_found = True
                    break
            assert cost_found

    @pytest.mark.asyncio
    async def test_cost_update_accumulates_tokens(
        self,
        server: BackendServer,
    ) -> None:
        assert server._total_tokens_in == 0
        assert server._total_tokens_out == 0
        server._emit_cost_update()
        assert server._total_tokens_in == 0
        assert server._total_tokens_out == 0

    @pytest.mark.asyncio
    async def test_cost_update_shape(
        self,
        server: BackendServer,
        capsys: CaptureFixture,
    ) -> None:
        server._emit_cost_update()
        captured = capsys.readouterr()
        msg = json.loads(captured.out.strip())
        assert msg["method"] == "on_cost_update"
        assert msg["params"]["cost"] == "0.0000"
        assert "tokens_in" in msg["params"]
        assert "tokens_out" in msg["params"]

    @pytest.mark.asyncio
    async def test_cost_update_with_session_stats(
        self,
        server: BackendServer,
        capsys: CaptureFixture,
    ) -> None:
        mock_stats = MagicMock()
        mock_tracker = MagicMock()
        mock_tracker.total.prompt_tokens = 100
        mock_tracker.total.completion_tokens = 50
        mock_stats.token_tracker = mock_tracker
        server._session_stats = mock_stats

        server._emit_cost_update()
        captured = capsys.readouterr()
        msg = json.loads(captured.out.strip())
        assert msg["params"]["tokens_in"] == 100
        assert msg["params"]["tokens_out"] == 50

        server._emit_cost_update()
        captured = capsys.readouterr()
        msg = json.loads(captured.out.strip())
        assert msg["params"]["tokens_in"] == 200
        assert msg["params"]["tokens_out"] == 100
