"""Transport-agnostic conformance checks for backend hosts.

These tests exercise the real ``BackendServer`` application surface through
both stdio and TCP host adapters so contract coverage is no longer limited to
host-specific unit tests.
"""

from __future__ import annotations

import asyncio
import io
import json
import socket
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from autocode.agent.completion import SessionStats
from autocode.agent.cost_dashboard import CostDashboard
from autocode.agent.token_tracker import TokenTracker
from autocode.backend.server import BackendServer
from autocode.backend.stdio_host import StdioJsonRpcHost
from autocode.backend.tcp_host import TcpJsonRpcHost
from autocode.backend.transport import StdoutTransport
from autocode.config import AutoCodeConfig
from autocode.session.checkpoint_store import CheckpointStore
from autocode.session.task_store import TaskStore


def _make_server(tmp_path: Path) -> BackendServer:
    config = AutoCodeConfig()
    config.tui.session_db_path = str(tmp_path / "sessions.db")
    config.logging.log_dir = str(tmp_path / "logs")
    config.logging.file_enabled = False
    return BackendServer(config=config, project_root=tmp_path)


def test_backend_telemetry_emit_preserves_attached_transport(tmp_path: Path) -> None:
    server = _make_server(tmp_path)
    stdout = io.StringIO()
    server.set_transport(StdoutTransport(stdout))

    attached = server._transport
    server._emit_telemetry("test_event", {})

    assert server._transport is attached


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _task_entry(task_id: str, title: str, status: str = "open") -> MagicMock:
    task = MagicMock()
    task.model_dump.return_value = {
        "id": task_id,
        "title": title,
        "status": status,
    }
    return task


async def _run_stdio_contract(
    server: BackendServer,
    requests: list[dict[str, object]],
) -> list[dict[str, object]]:
    stdin = io.StringIO("".join(json.dumps(request) + "\n" for request in requests))
    stdout = io.StringIO()
    await StdioJsonRpcHost(server, stdin=stdin, stdout=stdout).run()
    return [
        json.loads(line)
        for line in stdout.getvalue().splitlines()
        if line.strip()
    ]


async def _run_stdio_chat_contract(
    server: BackendServer,
    request: dict[str, object],
    *,
    shutdown_id: int = 999,
) -> list[dict[str, object]]:
    stdin = io.StringIO(json.dumps(request) + "\n")
    stdout = io.StringIO()
    await StdioJsonRpcHost(server, stdin=stdin, stdout=stdout).run()
    if server._agent_task is not None and not server._agent_task.done():
        await server._agent_task
    await server.handle_shutdown(shutdown_id)
    return [
        json.loads(line)
        for line in stdout.getvalue().splitlines()
        if line.strip()
    ]


async def _run_tcp_contract(
    server: BackendServer,
    requests: list[dict[str, object]],
) -> list[dict[str, object]]:
    port = _free_tcp_port()
    host = TcpJsonRpcHost(server, bind_host="127.0.0.1", port=port)
    host_task = asyncio.create_task(host.run())
    reader = writer = None
    messages: list[dict[str, object]] = []
    try:
        for _ in range(50):
            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", port)
                break
            except OSError:
                await asyncio.sleep(0.02)
        assert reader is not None
        assert writer is not None

        messages.append(json.loads((await reader.readline()).decode("utf-8")))

        for request in requests:
            writer.write((json.dumps(request) + "\n").encode("utf-8"))
            await writer.drain()
            request_id = int(request["id"])
            while True:
                message = json.loads((await reader.readline()).decode("utf-8"))
                messages.append(message)
                if message.get("id") == request_id:
                    break
        return messages
    finally:
        if writer is not None:
            writer.close()
            await writer.wait_closed()
        server._running = False
        await asyncio.wait_for(host_task, timeout=2)


async def _run_tcp_chat_contract(
    server: BackendServer,
    request: dict[str, object],
    *,
    shutdown_id: int = 999,
) -> list[dict[str, object]]:
    port = _free_tcp_port()
    host = TcpJsonRpcHost(server, bind_host="127.0.0.1", port=port)
    host_task = asyncio.create_task(host.run())
    reader = writer = None
    messages: list[dict[str, object]] = []
    try:
        for _ in range(50):
            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", port)
                break
            except OSError:
                await asyncio.sleep(0.02)
        assert reader is not None
        assert writer is not None

        messages.append(json.loads((await reader.readline()).decode("utf-8")))
        writer.write((json.dumps(request) + "\n").encode("utf-8"))
        await writer.drain()

        while True:
            message = json.loads((await reader.readline()).decode("utf-8"))
            messages.append(message)
            if message.get("method") == "on_done":
                break

        writer.write(
            (
                json.dumps(
                    {"jsonrpc": "2.0", "id": shutdown_id, "method": "shutdown", "params": {}}
                )
                + "\n"
            ).encode("utf-8")
        )
        await writer.drain()
        while True:
            message = json.loads((await reader.readline()).decode("utf-8"))
            messages.append(message)
            if message.get("id") == shutdown_id:
                break
        return messages
    finally:
        if writer is not None:
            writer.close()
            await writer.wait_closed()
        server._running = False
        await asyncio.wait_for(host_task, timeout=2)


@pytest.mark.asyncio
@pytest.mark.parametrize("host_kind", ["stdio", "tcp"])
async def test_transport_conformance_session_and_command_catalog(
    tmp_path: Path,
    host_kind: str,
) -> None:
    server = _make_server(tmp_path)
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "session.list", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "command.list", "params": {}},
        {"jsonrpc": "2.0", "id": 3, "method": "shutdown", "params": {}},
    ]

    if host_kind == "stdio":
        messages = await _run_stdio_contract(server, requests)
    else:
        messages = await _run_tcp_contract(server, requests)

    assert messages[0]["method"] == "on_status"
    session_response = next(message for message in messages if message.get("id") == 1)
    command_response = next(message for message in messages if message.get("id") == 2)
    shutdown_response = next(message for message in messages if message.get("id") == 3)

    assert "sessions" in session_response["result"]
    assert session_response["result"]["sessions"]
    assert "commands" in command_response["result"]
    assert any(
        command["name"] == "help"
        for command in command_response["result"]["commands"]
    )
    assert shutdown_response["result"] == {"ok": True}


@pytest.mark.asyncio
@pytest.mark.parametrize("host_kind", ["stdio", "tcp"])
async def test_transport_conformance_session_transition_status_visibility(
    tmp_path: Path,
    host_kind: str,
) -> None:
    server = _make_server(tmp_path)
    requests = [
        {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "session.new",
            "params": {"title": "Conformance Session"},
        },
        {"jsonrpc": "2.0", "id": 11, "method": "shutdown", "params": {}},
    ]

    if host_kind == "stdio":
        messages = await _run_stdio_contract(server, requests)
    else:
        messages = await _run_tcp_contract(server, requests)

    status_messages = [message for message in messages if message.get("method") == "on_status"]
    response = next(message for message in messages if message.get("id") == 10)

    assert len(status_messages) >= 2
    assert response["result"]["title"] == "Conformance Session"
    assert response["result"]["session_id"] == status_messages[-1]["params"]["session_id"]


@pytest.mark.asyncio
@pytest.mark.parametrize("host_kind", ["stdio", "tcp"])
async def test_transport_conformance_chat_warning_error_order(
    tmp_path: Path,
    host_kind: str,
) -> None:
    server = _make_server(tmp_path)

    class WarningLoop:
        def __init__(self, session_id: str) -> None:
            self.session_id = session_id

        async def run(self, _message: str, **kwargs: object) -> None:
            on_retry_notice = kwargs["on_retry_notice"]
            on_retry_notice("WARNING: Could not reach the configured gateway at http://localhost:4000/v1.")
            raise RuntimeError("Could not reach the configured gateway at http://localhost:4000/v1.")

    server._ensure_agent_loop = lambda: WarningLoop(server.session_id)  # type: ignore[method-assign]
    if host_kind == "stdio":
        messages = await _run_stdio_chat_contract(
            server,
            {"jsonrpc": "2.0", "id": 21, "method": "chat", "params": {"message": "hello"}},
            shutdown_id=22,
        )
    else:
        messages = await _run_tcp_chat_contract(
            server,
            {"jsonrpc": "2.0", "id": 21, "method": "chat", "params": {"message": "hello"}},
            shutdown_id=22,
        )

    methods = [message.get("method") for message in messages if message.get("method")]
    assert "on_chat_ack" in methods
    assert "on_warning" in methods
    assert "on_error" in methods
    assert "on_done" in methods
    assert methods.index("on_chat_ack") < methods.index("on_warning")
    assert methods.index("on_warning") < methods.index("on_error")
    assert methods.index("on_error") < methods.index("on_done")


@pytest.mark.asyncio
@pytest.mark.parametrize("host_kind", ["stdio", "tcp"])
async def test_transport_conformance_chat_streams_thinking_tokens_and_update_task_state(
    tmp_path: Path,
    host_kind: str,
) -> None:
    server = _make_server(tmp_path)
    server._task_store = MagicMock()
    server._task_store.list_tasks.return_value = [_task_entry("t1", "Task 1", status="in_progress")]
    server._subagent_manager = MagicMock()
    server._subagent_manager.list_all.return_value = [
        {"id": "s1", "role": "research", "status": "running"}
    ]

    class StreamingLoop:
        def __init__(self, session_id: str) -> None:
            self.session_id = session_id

        async def run(self, _message: str, **kwargs: object) -> None:
            kwargs["on_thinking_chunk"]("thinking")
            kwargs["on_chunk"]("hello")
            kwargs["on_tool_call"]("update_task", "completed", "updated")

    server._ensure_agent_loop = lambda: StreamingLoop(server.session_id)  # type: ignore[method-assign]
    if host_kind == "stdio":
        messages = await _run_stdio_chat_contract(
            server,
            {"jsonrpc": "2.0", "id": 31, "method": "chat", "params": {"message": "hello"}},
            shutdown_id=32,
        )
    else:
        messages = await _run_tcp_chat_contract(
            server,
            {"jsonrpc": "2.0", "id": 31, "method": "chat", "params": {"message": "hello"}},
            shutdown_id=32,
        )

    methods = [message.get("method") for message in messages if message.get("method")]
    assert "on_chat_ack" in methods
    assert "on_thinking" in methods
    assert "on_token" in methods
    assert "on_tool_call" in methods
    assert "on_task_state" in methods
    assert "on_done" in methods
    assert methods.index("on_chat_ack") < methods.index("on_thinking")
    assert methods.index("on_thinking") < methods.index("on_token")
    assert methods.index("on_token") < methods.index("on_tool_call")
    assert methods.index("on_tool_call") < methods.index("on_task_state")
    assert methods.index("on_task_state") < methods.index("on_done")

    task_state = next(message for message in messages if message.get("method") == "on_task_state")
    assert task_state["params"] == {
        "tasks": [{"id": "t1", "title": "Task 1", "status": "in_progress"}],
        "subagents": [{"id": "s1", "role": "research", "status": "running"}],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("host_kind", ["stdio", "tcp"])
async def test_transport_conformance_chat_surfaces_search_payload_and_cost_limit(
    tmp_path: Path,
    host_kind: str,
) -> None:
    server = _make_server(tmp_path)
    dashboard = CostDashboard()
    tracker = TokenTracker(cost_dashboard=dashboard, cost_limit_usd=0.001)
    stats = SessionStats()
    stats.token_tracker = tracker
    server._session_stats = stats

    class SearchAndCostLoop:
        def __init__(self, session_id: str) -> None:
            self.session_id = session_id

        async def run(self, _message: str, **kwargs: object) -> None:
            on_tool_call = kwargs["on_tool_call"]
            tracker.record(
                prompt_tokens=1_000,
                completion_tokens=25,
                provider="openrouter / coding",
                cached_input_tokens=250,
            )
            on_tool_call(
                "search_code",
                "completed",
                "src/example.py:7:def target() -> None:",
            )

    server._ensure_agent_loop = lambda: SearchAndCostLoop(server.session_id)  # type: ignore[method-assign]
    if host_kind == "stdio":
        messages = await _run_stdio_chat_contract(
            server,
            {"jsonrpc": "2.0", "id": 35, "method": "chat", "params": {"message": "search"}},
            shutdown_id=36,
        )
    else:
        messages = await _run_tcp_chat_contract(
            server,
            {"jsonrpc": "2.0", "id": 35, "method": "chat", "params": {"message": "search"}},
            shutdown_id=36,
        )

    methods = [message.get("method") for message in messages if message.get("method")]
    assert "on_tool_call" in methods
    assert "on_warning" in methods
    assert "on_cost_update" in methods
    assert "on_done" in methods
    assert methods.index("on_tool_call") < methods.index("on_warning")
    assert methods.index("on_warning") < methods.index("on_cost_update")
    assert methods.index("on_cost_update") < methods.index("on_done")

    tool_message = next(message for message in messages if message.get("method") == "on_tool_call")
    assert tool_message["params"]["result_payload"] == {
        "kind": "search",
        "query": "search_code",
        "hits": [
            {
                "path": "src/example.py",
                "line": 7,
                "snippet": "def target() -> None:",
            }
        ],
    }

    warning = next(message for message in messages if message.get("method") == "on_warning")
    assert "Session cost limit reached" in warning["params"]["message"]
    assert "$0.0010 threshold" in warning["params"]["message"]
    cost_update = next(message for message in messages if message.get("method") == "on_cost_update")
    assert cost_update["params"]["cost"] == "$0.0024"
    assert cost_update["params"]["tokens_in"] == 1_000
    assert cost_update["params"]["tokens_out"] == 25


@pytest.mark.asyncio
@pytest.mark.parametrize("host_kind", ["stdio", "tcp"])
async def test_transport_conformance_task_subagent_and_memory_surfaces(
    tmp_path: Path,
    host_kind: str,
) -> None:
    server = _make_server(tmp_path)
    server._task_store = MagicMock()
    server._task_store.list_tasks.return_value = [_task_entry("t2", "Task 2", status="running")]
    server._subagent_manager = MagicMock()
    server._subagent_manager.list_all.return_value = [
        {"id": "s2", "role": "coding", "status": "completed"}
    ]
    server._memory_store = MagicMock()
    server._memory_store.get_memories.return_value = [
        {"id": "m1", "content": "Remember this", "score": 1.0}
    ]
    requests = [
        {"jsonrpc": "2.0", "id": 41, "method": "task.list", "params": {}},
        {"jsonrpc": "2.0", "id": 42, "method": "subagent.list", "params": {}},
        {"jsonrpc": "2.0", "id": 43, "method": "memory.list", "params": {}},
        {"jsonrpc": "2.0", "id": 44, "method": "shutdown", "params": {}},
    ]

    if host_kind == "stdio":
        messages = await _run_stdio_contract(server, requests)
    else:
        messages = await _run_tcp_contract(server, requests)

    task_response = next(message for message in messages if message.get("id") == 41)
    subagent_response = next(message for message in messages if message.get("id") == 42)
    memory_response = next(message for message in messages if message.get("id") == 43)

    assert task_response["result"] == {
        "tasks": [{"id": "t2", "title": "Task 2", "status": "running"}]
    }
    assert subagent_response["result"] == {
        "subagents": [{"id": "s2", "role": "coding", "status": "completed"}]
    }
    assert memory_response["result"] == {
        "memories": [{"id": "m1", "content": "Remember this", "score": 1.0}]
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("host_kind", ["stdio", "tcp"])
async def test_transport_conformance_checkpoint_restore_rehydrates_messages(
    tmp_path: Path,
    host_kind: str,
) -> None:
    server = _make_server(tmp_path)
    conn = server.session_store.get_connection()
    server._task_store = TaskStore(conn, server.session_id)
    server._checkpoint_store = CheckpointStore(conn, server.session_id)

    server.session_store.add_message(server.session_id, "user", "save me")
    cp_id = server._checkpoint_store.save_checkpoint(
        server._task_store,
        "transport checkpoint",
        context_summary="transport restore summary",
        session_store=server.session_store,
    )
    server.session_store.add_message(server.session_id, "user", "after checkpoint")

    requests = [
        {
            "jsonrpc": "2.0",
            "id": 51,
            "method": "checkpoint.restore",
            "params": {"checkpoint_id": cp_id},
        },
        {"jsonrpc": "2.0", "id": 52, "method": "shutdown", "params": {}},
    ]

    if host_kind == "stdio":
        messages = await _run_stdio_contract(server, requests)
    else:
        messages = await _run_tcp_contract(server, requests)

    restore_response = next(message for message in messages if message.get("id") == 51)
    assert restore_response["result"] == {
        "ok": True,
        "checkpoint_id": cp_id,
        "label": "transport checkpoint",
        "active_files": [],
        "restored_messages": 1,
        "restored_tool_calls": 0,
    }

    contents = [
        message.content
        for message in server.session_store.get_messages(server.session_id)
    ]
    assert "save me" in contents
    assert "after checkpoint" not in contents
    assert any("transport restore summary" in content for content in contents)
