"""Tests for edit strategy abstraction."""

from __future__ import annotations

from autocode.agent.edit_strategy import (
    EditBlockStrategy,
    EditRequest,
    WholeFileStrategy,
    select_strategy,
    STRATEGIES,
)


def test_editblock_parse() -> None:
    """EditBlock parses SEARCH/REPLACE blocks."""
    strategy = EditBlockStrategy()
    request = EditRequest(
        file="app.py",
        instruction="Fix the bug",
        current_content="def add(a, b):\n    return a - b\n",
    )
    response = (
        "<<<<<<< SEARCH\n"
        "    return a - b\n"
        "=======\n"
        "    return a + b\n"
        ">>>>>>> REPLACE"
    )

    result = strategy.parse_response(response, request)
    assert result.success
    assert "return a + b" in result.new_content
    assert "return a - b" not in result.new_content


def test_editblock_no_match() -> None:
    """EditBlock fails when SEARCH block not found."""
    strategy = EditBlockStrategy()
    request = EditRequest(
        file="app.py", instruction="Fix",
        current_content="x = 1\n",
    )
    response = (
        "<<<<<<< SEARCH\n"
        "y = 2\n"
        "=======\n"
        "y = 3\n"
        ">>>>>>> REPLACE"
    )

    result = strategy.parse_response(response, request)
    assert not result.success
    assert "not found" in result.error


def test_wholefile_parse() -> None:
    """WholeFile extracts code from markdown block."""
    strategy = WholeFileStrategy()
    request = EditRequest(
        file="app.py", instruction="Rewrite",
        current_content="old\n",
    )
    response = "Here's the new file:\n```python\nnew content\n```"

    result = strategy.parse_response(response, request)
    assert result.success
    assert "new content" in result.new_content


def test_wholefile_no_code_block() -> None:
    """WholeFile fails without code block."""
    strategy = WholeFileStrategy()
    request = EditRequest(file="app.py", instruction="Fix", current_content="")
    result = strategy.parse_response("Just some text", request)
    assert not result.success


def test_select_strategy_by_model() -> None:
    """Strategy selected based on model name."""
    assert select_strategy("gpt-4o").name == "editblock"
    assert select_strategy("llama-3").name == "wholefile"
    assert select_strategy("claude-3").name == "editblock"
    assert select_strategy("qwen2.5").name == "wholefile"


def test_select_strategy_default() -> None:
    """Unknown model defaults to editblock."""
    assert select_strategy("unknown-model").name == "editblock"
    assert select_strategy("").name == "editblock"


def test_all_strategies_registered() -> None:
    """All strategies exist in registry."""
    assert "editblock" in STRATEGIES
    assert "wholefile" in STRATEGIES
    assert "udiff" in STRATEGIES


def test_editblock_prompt_format() -> None:
    """EditBlock prompt includes file and instruction."""
    strategy = EditBlockStrategy()
    request = EditRequest(
        file="src/app.py",
        instruction="Add error handling",
        current_content="def main(): pass\n",
    )
    prompt = strategy.format_prompt(request)
    assert "src/app.py" in prompt
    assert "Add error handling" in prompt
    assert "SEARCH" in prompt
    assert "REPLACE" in prompt
