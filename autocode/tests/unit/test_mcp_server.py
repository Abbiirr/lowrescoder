"""Tests for MCP Server — read-only tools with security enforcement."""

from __future__ import annotations

import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from autocode.external.mcp_server import MCP_TOOLS, MCPServer, MCPServerConfig


def test_mcp_tools_defined() -> None:
    """MCP exposes 6 read-only tools."""
    assert len(MCP_TOOLS) == 6
    assert "search_code" in MCP_TOOLS
    assert "find_definition" in MCP_TOOLS
    assert "read_file" in MCP_TOOLS


def test_mcp_server_tools() -> None:
    """Server reports available tools."""
    server = MCPServer()
    assert server.tools == MCP_TOOLS


def test_path_validation_allowed(tmp_path: Path) -> None:
    """Paths within project root are allowed."""
    config = MCPServerConfig(project_root=tmp_path)
    server = MCPServer(config)

    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1")

    result = server.validate_path(str(test_file))
    assert result == test_file.resolve()


def test_path_validation_blocked(tmp_path: Path) -> None:
    """Paths outside project root are blocked."""
    config = MCPServerConfig(project_root=tmp_path)
    server = MCPServer(config)

    with pytest.raises(ValueError, match="outside allowed roots"):
        server.validate_path("/etc/passwd")


def test_handle_tool_call_valid(tmp_path: Path) -> None:
    """Valid tool calls succeed."""
    config = MCPServerConfig(project_root=tmp_path)
    server = MCPServer(config)

    result = server.handle_tool_call(
        "search_code", {"query": "def main"}, caller="claude",
    )
    assert result["status"] == "ok"


def test_handle_tool_call_unknown() -> None:
    """Unknown tools return error."""
    server = MCPServer()
    result = server.handle_tool_call("delete_everything", {})
    assert "error" in result
    assert "Unknown tool" in result["error"]


def test_handle_tool_call_blocked_path(tmp_path: Path) -> None:
    """Tool calls with paths outside root are blocked."""
    config = MCPServerConfig(project_root=tmp_path)
    server = MCPServer(config)

    result = server.handle_tool_call(
        "read_file", {"path": "/etc/shadow"}, caller="attacker",
    )
    assert "error" in result
    assert "outside allowed" in result["error"]


def test_audit_log(tmp_path: Path) -> None:
    """All tool calls are audit logged."""
    config = MCPServerConfig(project_root=tmp_path)
    server = MCPServer(config)

    server.handle_tool_call("search_code", {"query": "test"}, caller="claude")
    server.handle_tool_call("read_file", {"path": "/etc/passwd"}, caller="bad")

    log = server.audit_log
    assert len(log) == 2
    assert log[0].tool_name == "search_code"
    assert log[0].allowed
    assert log[1].tool_name == "read_file"
    assert not log[1].allowed  # blocked path


def test_localhost_default() -> None:
    """Server binds to localhost by default."""
    config = MCPServerConfig()
    assert config.bind_host == "127.0.0.1"
    assert config.transport == "stdio"


def test_narrowed_allowed_paths_constrains_search(tmp_path: Path) -> None:
    """Search tools only search within allowed_paths, not broad project_root."""
    # Create project with two subdirs
    allowed = tmp_path / "allowed"
    forbidden = tmp_path / "forbidden"
    allowed.mkdir()
    forbidden.mkdir()
    (allowed / "good.py").write_text("def allowed_func():\n    pass\n")
    (forbidden / "secret.py").write_text("def forbidden_func():\n    pass\n")

    # Narrow allowed_paths to only the allowed subdir
    config = MCPServerConfig(
        project_root=tmp_path,
        allowed_paths=[allowed],
    )
    server = MCPServer(config)

    # search_code should only find in allowed/
    result = server.handle_tool_call("search_code", {"query": "def "})
    matches = result.get("result", [])
    match_text = "\n".join(str(m) for m in matches)
    assert "allowed_func" in match_text
    assert "forbidden_func" not in match_text

    # find_definition should also be constrained
    result2 = server.handle_tool_call("find_definition", {"symbol": "forbidden_func"})
    matches2 = result2.get("result", [])
    assert len(matches2) == 0 or not any("forbidden" in str(m) for m in matches2)


def test_run_stdio_exits_cleanly_on_eof(tmp_path: Path) -> None:
    """stdio transport returns cleanly when the client closes stdin."""
    config = MCPServerConfig(project_root=tmp_path, transport="stdio")
    server = MCPServer(config)
    output = io.StringIO()

    server.run(input_stream=io.StringIO(""), output_stream=output)

    assert output.getvalue() == ""


def test_run_stdio_handles_tools_list_json_rpc(tmp_path: Path) -> None:
    """stdio transport exposes tools/list as a JSON-RPC response."""
    config = MCPServerConfig(project_root=tmp_path, transport="stdio")
    server = MCPServer(config)
    request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    output = io.StringIO()

    server.run(input_stream=io.StringIO(json.dumps(request) + "\n"), output_stream=output)

    response = json.loads(output.getvalue())
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    tool_names = {tool["name"] for tool in response["result"]["tools"]}
    assert tool_names == set(MCP_TOOLS)


def test_audit_log_path_persists_jsonl_records(tmp_path: Path) -> None:
    """Configured audit-log path receives JSONL MCPToolCall records."""
    audit_path = tmp_path / "logs" / "mcp_audit.jsonl"
    config = MCPServerConfig(
        project_root=tmp_path,
        transport="stdio",
        audit_log_path=audit_path,
    )
    server = MCPServer(config)

    server.handle_tool_call("search_code", {"query": "missing"}, caller="client-a")
    server.handle_tool_call("read_file", {"path": "/etc/passwd"}, caller="client-b")

    records = [json.loads(line) for line in audit_path.read_text().splitlines()]
    assert [record["tool_name"] for record in records] == ["search_code", "read_file"]
    assert records[0]["caller"] == "client-a"
    assert records[0]["allowed"] is True
    assert records[1]["allowed"] is False
    assert "outside allowed" in records[1]["result_summary"]


def test_run_stdio_returns_cleanly_on_keyboard_interrupt(tmp_path: Path) -> None:
    """Lifecycle shutdown returns cleanly when the host interrupts stdio."""

    class InterruptingInput:
        def __iter__(self) -> InterruptingInput:
            return self

        def __next__(self) -> str:
            raise KeyboardInterrupt

    config = MCPServerConfig(project_root=tmp_path, transport="stdio")
    server = MCPServer(config)
    output = io.StringIO()

    server.run(input_stream=InterruptingInput(), output_stream=output)  # type: ignore[arg-type]

    assert output.getvalue() == ""
    assert server.is_shutdown


def test_stdio_transport_handles_concurrent_clients_independently(tmp_path: Path) -> None:
    """Two stdio clients can use one server without sharing JSON-RPC ids/state."""
    audit_path = tmp_path / "mcp_audit.jsonl"
    config = MCPServerConfig(
        project_root=tmp_path,
        transport="stdio",
        audit_log_path=audit_path,
    )
    server = MCPServer(config)
    (tmp_path / "a.py").write_text("def alpha():\n    pass\n")

    def run_client(request_id: int) -> dict[str, object]:
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": "read_file", "arguments": {"path": str(tmp_path / "a.py")}},
        }
        output = io.StringIO()
        server.run(input_stream=io.StringIO(json.dumps(request) + "\n"), output_stream=output)
        return json.loads(output.getvalue())

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(run_client, [101, 202]))

    assert {response["id"] for response in responses} == {101, 202}
    assert all("result" in response for response in responses)
    assert len(server.audit_log) == 2
    assert len(audit_path.read_text().splitlines()) == 2
