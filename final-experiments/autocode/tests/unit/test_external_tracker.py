"""Tests for ExternalToolTracker — runtime tool discovery."""

from __future__ import annotations

from autocode.external.harness_adapter import HarnessKind
from autocode.external.tracker import KNOWN_TOOLS, ExternalTool, ExternalToolTracker


def test_known_tools_list() -> None:
    """Known tools includes the first-wave external harness targets."""
    assert "claude_code" in KNOWN_TOOLS
    assert "codex" in KNOWN_TOOLS
    assert "opencode" in KNOWN_TOOLS
    assert "forge" in KNOWN_TOOLS
    assert "gemini" in KNOWN_TOOLS


def test_discover_returns_list() -> None:
    """Discover returns a list of ExternalTool objects."""
    tracker = ExternalToolTracker()
    tools = tracker.discover()
    assert isinstance(tools, list)
    assert len(tools) == len(KNOWN_TOOLS)
    assert all(isinstance(t, ExternalTool) for t in tools)


def test_external_tool_structure() -> None:
    """ExternalTool has expected fields."""
    tool = ExternalTool(
        name="test_tool",
        binary="test-cli",
        version="1.0.0",
        available=True,
        supports_mcp=True,
    )
    assert tool.name == "test_tool"
    assert tool.available
    assert tool.supports_mcp


def test_external_tool_to_probe_maps_capabilities() -> None:
    """Discovery metadata converts into the canonical adapter probe format."""
    tool = ExternalTool(
        name="forge",
        binary="forge",
        version="2.3.2",
        available=True,
    )
    probe = tool.to_probe()
    assert probe.kind == HarnessKind.FORGE
    assert probe.available is True


def test_available_tools_filters() -> None:
    """available_tools only returns tools found on PATH."""
    tracker = ExternalToolTracker()
    tracker.discover()
    available = tracker.available_tools
    # All available tools should have available=True
    assert all(t.available for t in available)


def test_get_by_name() -> None:
    """Can retrieve a tool by name after discovery."""
    tracker = ExternalToolTracker()
    tracker.discover()
    # At least one tool should be queryable
    for name in KNOWN_TOOLS:
        tool = tracker.get(name)
        assert tool is not None
        assert tool.name == name
