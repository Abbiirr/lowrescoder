"""Tests for the context assembler (Sprint 3F)."""

from __future__ import annotations

from autocode.core.context import ContextAssembler
from autocode.core.types import CodeChunk, SearchResult


def _make_result(content: str, score: float = 0.5) -> SearchResult:
    """Helper to create a SearchResult for testing."""
    return SearchResult(
        chunk=CodeChunk(
            content=content,
            file_path="test.py",
            language="python",
            start_line=1,
            end_line=10,
            chunk_type="function",
        ),
        score=score,
        match_type="bm25",
    )


class TestContextAssembler:
    def test_assemble_all_sections(self):
        asm = ContextAssembler(context_budget=5000)
        result = asm.assemble(
            query="test query",
            rules="Rule 1: Do X\nRule 2: Do Y",
            repomap="# Map\n- func: hello",
            search_results=[_make_result("def hello(): pass")],
            current_file="# current file content",
            history="User asked about X",
        )

        assert "Project Rules" in result
        assert "Repo Map" in result
        assert "Relevant Code" in result
        assert "Current File" in result
        assert "Recent Context" in result

    def test_assemble_empty(self):
        asm = ContextAssembler()
        result = asm.assemble(query="test")
        assert result == ""

    def test_budget_enforcement(self):
        """Total context should not exceed budget."""
        asm = ContextAssembler(context_budget=100)

        # Provide very long inputs
        long_rules = "x" * 10000
        long_repomap = "y" * 10000
        long_file = "z" * 10000

        result = asm.assemble(
            query="test",
            rules=long_rules,
            repomap=long_repomap,
            current_file=long_file,
        )

        # Budget is 100 tokens * 4 chars = 400 chars max
        assert len(result) <= 100 * 4 + 100  # Allow some overhead for section headers

    def test_priority_order(self):
        """Rules should appear before repomap which appears before search."""
        asm = ContextAssembler()
        result = asm.assemble(
            query="test",
            rules="RULES_HERE",
            repomap="MAP_HERE",
            search_results=[_make_result("CODE_HERE")],
        )

        rules_pos = result.find("RULES_HERE")
        map_pos = result.find("MAP_HERE")
        code_pos = result.find("CODE_HERE")

        assert rules_pos < map_pos < code_pos

    def test_search_results_formatting(self):
        asm = ContextAssembler()
        results = [
            _make_result("def hello(): pass", score=0.9),
            _make_result("def world(): pass", score=0.7),
        ]
        result = asm.assemble(query="test", search_results=results)
        assert "hello" in result
        assert "world" in result
        assert "0.900" in result  # Score formatting

    def test_token_count(self):
        asm = ContextAssembler()
        assert asm.token_count("hello world") == len("hello world") // 4

    def test_rules_only(self):
        asm = ContextAssembler()
        result = asm.assemble(query="test", rules="Only rules")
        assert "Only rules" in result
        assert "Repo Map" not in result

    def test_search_only(self):
        asm = ContextAssembler()
        result = asm.assemble(
            query="test",
            search_results=[_make_result("some code")],
        )
        assert "some code" in result
        assert "Project Rules" not in result

    def test_large_budget(self):
        """Large budgets should not truncate small inputs."""
        asm = ContextAssembler(context_budget=10000)
        result = asm.assemble(
            query="test",
            rules="short rules",
            repomap="short map",
        )
        assert "short rules" in result
        assert "truncated" not in result
