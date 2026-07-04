"""Tests for tool compatibility shim."""

from __future__ import annotations

from autocode.agent.tool_shim import (
    ToolShim,
    parse_markdown_tool_calls,
    parse_tool_calls,
    parse_xml_tool_calls,
)


def test_xml_tool_calls() -> None:
    """Parse XML-style tool calls."""
    text = 'I will read the file. <function=read_file>{"path": "app.py"}</function>'
    calls = parse_xml_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].name == "read_file"
    assert calls[0].arguments["path"] == "app.py"


def test_xml_multiple_calls() -> None:
    """Parse multiple XML tool calls."""
    text = (
        '<function=read_file>{"path": "a.py"}</function> '
        'then <function=write_file>{"path": "b.py", "content": "x"}</function>'
    )
    calls = parse_xml_tool_calls(text)
    assert len(calls) == 2


def test_markdown_tool_calls() -> None:
    """Parse markdown-style tool calls."""
    text = '```tool\n{"name": "read_file", "args": {"path": "app.py"}}\n```'
    calls = parse_markdown_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].name == "read_file"


def test_parse_auto_detect() -> None:
    """Auto-detect format."""
    xml = '<function=run_command>{"command": "ls"}</function>'
    calls = parse_tool_calls(xml)
    assert len(calls) == 1
    assert calls[0].name == "run_command"


def test_parse_no_calls() -> None:
    """No tool calls in text."""
    calls = parse_tool_calls("Just regular text without any tool calls.")
    assert len(calls) == 0


def test_shim_filters_by_available() -> None:
    """Shim filters to available tools only."""
    shim = ToolShim(available_tools=["read_file"])
    text = (
        '<function=read_file>{"path": "a.py"}</function> '
        '<function=delete_file>{"path": "b.py"}</function>'
    )
    calls = shim.extract(text)
    assert len(calls) == 1
    assert calls[0].name == "read_file"


def test_shim_no_filter() -> None:
    """Shim without filter returns all calls."""
    shim = ToolShim()
    text = '<function=anything>{"x": 1}</function>'
    calls = shim.extract(text)
    assert len(calls) == 1
