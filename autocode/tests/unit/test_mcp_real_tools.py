"""Tests for MCP server with real L1/L2 tool execution."""

from __future__ import annotations

from pathlib import Path

from autocode.external.mcp_server import MCPServer, MCPServerConfig


def test_read_file_real(tmp_path: Path) -> None:
    """read_file returns actual file content."""
    test_file = tmp_path / "hello.py"
    test_file.write_text("x = 1\ny = 2\nz = 3\n")

    config = MCPServerConfig(project_root=tmp_path)
    server = MCPServer(config)

    result = server.handle_tool_call("read_file", {"path": str(test_file)})
    assert result["status"] == "ok"
    assert "x = 1" in result["result"]
    assert "z = 3" in result["result"]


def test_read_file_with_line_range(tmp_path: Path) -> None:
    """read_file respects start_line and end_line."""
    test_file = tmp_path / "lines.py"
    test_file.write_text("line0\nline1\nline2\nline3\nline4\n")

    config = MCPServerConfig(project_root=tmp_path)
    server = MCPServer(config)

    result = server.handle_tool_call("read_file", {
        "path": str(test_file), "start_line": 1, "end_line": 3,
    })
    assert result["status"] == "ok"
    assert "line1" in result["result"]
    assert "line2" in result["result"]
    assert "line0" not in result["result"]


def test_list_symbols_real(tmp_path: Path) -> None:
    """list_symbols extracts function and class definitions."""
    test_file = tmp_path / "module.py"
    test_file.write_text(
        "class MyClass:\n    pass\n\n"
        "def my_function():\n    pass\n\n"
        "async def async_func():\n    pass\n"
    )

    config = MCPServerConfig(project_root=tmp_path)
    server = MCPServer(config)

    result = server.handle_tool_call("list_symbols", {"path": str(test_file)})
    assert result["status"] == "ok"
    symbols = result["result"]
    assert any("MyClass" in str(s) for s in symbols)
    assert any("my_function" in str(s) for s in symbols)
    assert any("async_func" in str(s) for s in symbols)


def test_search_code_real(tmp_path: Path) -> None:
    """search_code finds matches in Python files."""
    (tmp_path / "app.py").write_text("def main():\n    print('hello')\n")
    (tmp_path / "utils.py").write_text("def helper():\n    return 42\n")

    config = MCPServerConfig(project_root=tmp_path)
    server = MCPServer(config)

    result = server.handle_tool_call("search_code", {"query": "def main"})
    assert result["status"] == "ok"
    assert any("main" in str(m) for m in result["result"])


def test_find_definition_real(tmp_path: Path) -> None:
    """find_definition locates function/class definitions."""
    (tmp_path / "service.py").write_text("class UserService:\n    pass\n")

    config = MCPServerConfig(project_root=tmp_path)
    server = MCPServer(config)

    result = server.handle_tool_call("find_definition", {"symbol": "UserService"})
    assert result["status"] == "ok"
    assert any("UserService" in str(m) for m in result["result"])


def test_get_diagnostics_valid(tmp_path: Path) -> None:
    """get_diagnostics passes on valid Python."""
    (tmp_path / "good.py").write_text("x = 1\n")

    config = MCPServerConfig(project_root=tmp_path)
    server = MCPServer(config)

    result = server.handle_tool_call("get_diagnostics", {"path": str(tmp_path / "good.py")})
    assert result["status"] == "ok"
    assert "No syntax errors" in result["result"]


def test_get_diagnostics_invalid(tmp_path: Path) -> None:
    """get_diagnostics catches syntax errors."""
    (tmp_path / "bad.py").write_text("def broken(\n")

    config = MCPServerConfig(project_root=tmp_path)
    server = MCPServer(config)

    result = server.handle_tool_call("get_diagnostics", {"path": str(tmp_path / "bad.py")})
    assert result["status"] == "ok"
    assert "SyntaxError" in result["result"] or "error" in result["result"].lower()


def test_llmloop_apply_real(tmp_path: Path) -> None:
    """LLMLOOP apply() makes real file edits."""
    from autocode.agent.llmloop import LLMLOOP, EditPlan, Edit, EditType

    target = tmp_path / "app.py"
    target.write_text("x = 1\ny = 2\n")

    loop = LLMLOOP(project_root=str(tmp_path))
    plan = EditPlan(
        file="app.py",
        edits=[
            Edit(type=EditType.REPLACE, file="app.py",
                 location="line 1",
                 old_content="x = 1", new_content="x = 42"),
        ],
    )

    modified = loop.apply(plan)
    assert "app.py" in modified
    assert "x = 42" in target.read_text()
    assert "y = 2" in target.read_text()  # untouched
