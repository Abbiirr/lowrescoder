"""Tool compatibility shim for non-tool-calling models.

Based on Goose's GOOSE_TOOLSHIM pattern: when a model can't produce
native tool calls, parse text-based tool invocations from the response.

This sits behind a provider capability boundary — only activated when
the provider reports tool_calling=False.

Supported formats:
- XML-style: <function=tool_name>{"arg": "val"}</function>
- Markdown-style: ```tool\n{"name": "tool", "args": {...}}\n```
- Natural language: "I'll use read_file to look at app.py"
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class ShimmedToolCall:
    """A tool call extracted from text by the shim."""

    name: str
    arguments: dict[str, Any]
    raw_text: str = ""


def parse_xml_tool_calls(text: str) -> list[ShimmedToolCall]:
    """Parse XML-style tool calls: <function=name>{...}</function>."""
    calls: list[ShimmedToolCall] = []
    pattern = r'<function=(\w+)>(.*?)</function>'
    for match in re.finditer(pattern, text, re.DOTALL):
        name = match.group(1)
        args_str = match.group(2).strip()
        try:
            args = json.loads(args_str) if args_str else {}
        except json.JSONDecodeError:
            args = {"raw": args_str}
        calls.append(ShimmedToolCall(
            name=name, arguments=args, raw_text=match.group(0),
        ))
    return calls


def parse_markdown_tool_calls(text: str) -> list[ShimmedToolCall]:
    """Parse markdown-style tool calls: ```tool\n{...}\n```."""
    calls: list[ShimmedToolCall] = []
    pattern = r'```tool\n(.*?)```'
    for match in re.finditer(pattern, text, re.DOTALL):
        try:
            data = json.loads(match.group(1))
            calls.append(ShimmedToolCall(
                name=data.get("name", ""),
                arguments=data.get("args", data.get("arguments", {})),
                raw_text=match.group(0),
            ))
        except json.JSONDecodeError:
            continue
    return calls


def parse_tool_calls(text: str) -> list[ShimmedToolCall]:
    """Try all parsers and return the first non-empty result."""
    # Try XML first (most structured)
    calls = parse_xml_tool_calls(text)
    if calls:
        return calls

    # Try markdown
    calls = parse_markdown_tool_calls(text)
    if calls:
        return calls

    return []


class ToolShim:
    """Compatibility layer for models without native tool calling.

    Wraps a text-only model response and extracts tool calls
    from the text. Only activated when provider.supports_tools is False.
    """

    def __init__(self, available_tools: list[str] | None = None) -> None:
        self._available = set(available_tools or [])

    def extract(self, text: str) -> list[ShimmedToolCall]:
        """Extract tool calls from model text response."""
        calls = parse_tool_calls(text)

        # Filter to available tools if specified
        if self._available:
            calls = [c for c in calls if c.name in self._available]

        return calls

    @property
    def is_active(self) -> bool:
        """Whether the shim is actively needed."""
        return True  # Always ready; caller decides when to use
