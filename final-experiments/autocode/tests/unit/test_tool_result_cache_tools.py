"""Agent-facing tool-result cache management tools."""

from __future__ import annotations

from autocode.agent.tool_result_cache import ToolResultCache
from autocode.agent.tools import create_default_registry


def _core_tool_names(registry) -> set[str]:
    return {
        schema["function"]["name"]
        for schema in registry.get_core_schemas_openai_format()
    }


def test_list_tool_results_registered_when_cache_provided() -> None:
    cache = ToolResultCache()
    cache.record("read_file", {"path": "a.py"}, "contents")

    registry = create_default_registry(project_root="/tmp", tool_result_cache=cache)
    tool = registry.get("list_tool_results")

    assert tool is not None
    result = tool.handler()
    assert "tr0001" in result
    assert "read_file" in result


def test_clear_tool_result_clears_by_tool_name() -> None:
    cache = ToolResultCache()
    cache.record("read_file", {"path": "a.py"}, "contents")
    cache.record("search_text", {"pattern": "TODO"}, "hits")

    registry = create_default_registry(project_root="/tmp", tool_result_cache=cache)
    tool = registry.get("clear_tool_result")

    assert tool is not None
    result = tool.handler(tool="read_file")
    assert "Cleared 1" in result
    assert [entry.tool for entry in cache.live_entries()] == ["search_text"]


def test_clear_tool_result_clears_single_id_alias() -> None:
    cache = ToolResultCache()
    first_id = cache.record("read_file", {"path": "a.py"}, "contents")
    cache.record("search_text", {"pattern": "TODO"}, "hits")

    registry = create_default_registry(project_root="/tmp", tool_result_cache=cache)
    tool = registry.get("clear_tool_result")

    assert tool is not None
    result = tool.handler(id=first_id)
    assert "Cleared 1" in result
    assert [entry.tool for entry in cache.live_entries()] == ["search_text"]


def test_cache_management_tools_are_core_visible() -> None:
    cache = ToolResultCache()
    registry = create_default_registry(project_root="/tmp", tool_result_cache=cache)

    core_names = _core_tool_names(registry)

    assert "list_tool_results" in core_names
    assert "clear_tool_result" in core_names
