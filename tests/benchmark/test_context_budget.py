"""Benchmark: Context budget compliance tests (Gate 2).

20 test queries verifying context assembly stays within 5000 token budget.
"""

from __future__ import annotations

import pytest

from hybridcoder.core.context import ContextAssembler
from hybridcoder.core.types import CodeChunk, SearchResult

pytestmark = pytest.mark.benchmark

# Approximate chars per token
CHARS_PER_TOKEN = 4


def _make_result(content: str, score: float = 0.5, file_path: str = "test.py") -> SearchResult:
    return SearchResult(
        chunk=CodeChunk(
            content=content,
            file_path=file_path,
            language="python",
            start_line=1,
            end_line=10,
            chunk_type="function",
        ),
        score=score,
        match_type="bm25",
    )


def _estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN


class TestContextBudget:
    """20 queries verifying context stays within budget."""

    def test_empty_context(self):
        asm = ContextAssembler(context_budget=5000)
        result = asm.assemble(query="test")
        assert _estimate_tokens(result) <= 5000

    def test_rules_only(self):
        asm = ContextAssembler(context_budget=5000)
        result = asm.assemble(query="test", rules="x" * 2000)
        assert _estimate_tokens(result) <= 5000

    def test_repomap_only(self):
        asm = ContextAssembler(context_budget=5000)
        result = asm.assemble(query="test", repomap="y" * 3000)
        assert _estimate_tokens(result) <= 5000

    def test_search_results_only(self):
        results = [_make_result("z" * 500) for _ in range(10)]
        asm = ContextAssembler(context_budget=5000)
        result = asm.assemble(query="test", search_results=results)
        assert _estimate_tokens(result) <= 5000

    def test_all_sections_filled(self):
        results = [_make_result("code " * 100) for _ in range(5)]
        asm = ContextAssembler(context_budget=5000)
        result = asm.assemble(
            query="test",
            rules="Rule: " * 50,
            repomap="Map: " * 100,
            search_results=results,
            current_file="File: " * 100,
            history="History: " * 100,
        )
        assert _estimate_tokens(result) <= 5000

    def test_oversized_rules(self):
        asm = ContextAssembler(context_budget=5000)
        result = asm.assemble(query="test", rules="x" * 50000)
        assert _estimate_tokens(result) <= 5000

    def test_oversized_repomap(self):
        asm = ContextAssembler(context_budget=5000)
        result = asm.assemble(query="test", repomap="y" * 50000)
        assert _estimate_tokens(result) <= 5000

    def test_oversized_search_results(self):
        results = [_make_result("z" * 5000) for _ in range(20)]
        asm = ContextAssembler(context_budget=5000)
        result = asm.assemble(query="test", search_results=results)
        assert _estimate_tokens(result) <= 5000

    def test_oversized_file(self):
        asm = ContextAssembler(context_budget=5000)
        result = asm.assemble(query="test", current_file="f" * 50000)
        assert _estimate_tokens(result) <= 5000

    def test_oversized_history(self):
        asm = ContextAssembler(context_budget=5000)
        result = asm.assemble(query="test", history="h" * 50000)
        assert _estimate_tokens(result) <= 5000

    def test_all_oversized(self):
        results = [_make_result("c" * 10000) for _ in range(10)]
        asm = ContextAssembler(context_budget=5000)
        result = asm.assemble(
            query="test",
            rules="r" * 10000,
            repomap="m" * 10000,
            search_results=results,
            current_file="f" * 10000,
            history="h" * 10000,
        )
        assert _estimate_tokens(result) <= 5100  # Allow small overhead for headers

    def test_small_budget(self):
        asm = ContextAssembler(context_budget=100)
        result = asm.assemble(
            query="test",
            rules="r" * 1000,
            repomap="m" * 1000,
        )
        assert _estimate_tokens(result) <= 150  # Small overhead allowed

    def test_large_budget(self):
        asm = ContextAssembler(context_budget=10000)
        result = asm.assemble(
            query="test",
            rules="short rule",
            repomap="short map",
        )
        assert _estimate_tokens(result) <= 10000

    def test_realistic_project(self):
        rules = "# CLAUDE.md\n- Use Python 3.11+\n- Run tests before commit\n"
        repomap = "## src/main.py\n- func: hello\n- class: App\n"
        results = [
            _make_result("def hello():\n    return 'hello'", score=0.9),
            _make_result("class App:\n    def run(self): pass", score=0.7),
        ]
        asm = ContextAssembler(context_budget=5000)
        result = asm.assemble(
            query="how does hello work",
            rules=rules,
            repomap=repomap,
            search_results=results,
        )
        assert _estimate_tokens(result) <= 5000
        assert "hello" in result

    def test_many_small_results(self):
        results = [_make_result(f"def func_{i}(): pass", score=0.5 + i * 0.01) for i in range(50)]
        asm = ContextAssembler(context_budget=5000)
        result = asm.assemble(query="test", search_results=results)
        assert _estimate_tokens(result) <= 5000

    def test_code_blocks_in_results(self):
        code = "def parse(source):\n    tree = parser.parse(source)\n    return tree\n"
        results = [_make_result(code, score=0.8)]
        asm = ContextAssembler(context_budget=5000)
        result = asm.assemble(query="test", search_results=results)
        assert "```python" in result
        assert _estimate_tokens(result) <= 5000

    def test_mixed_file_paths(self):
        results = [
            _make_result("content1", file_path="src/a.py"),
            _make_result("content2", file_path="tests/test_b.py"),
            _make_result("content3", file_path="lib/c.py"),
        ]
        asm = ContextAssembler(context_budget=5000)
        result = asm.assemble(query="test", search_results=results)
        assert _estimate_tokens(result) <= 5000

    def test_unicode_content(self):
        asm = ContextAssembler(context_budget=5000)
        result = asm.assemble(
            query="test",
            rules="# Regeln auf Deutsch: Verwende Python 3.11+",
            current_file="print('日本語テスト')",
        )
        assert _estimate_tokens(result) <= 5000

    def test_budget_5000_default(self):
        asm = ContextAssembler()  # Default 5000
        assert asm._budget == 5000

    def test_consistent_across_calls(self):
        asm = ContextAssembler(context_budget=5000)
        for i in range(5):
            result = asm.assemble(
                query=f"query {i}",
                rules="rule " * (i * 100),
                repomap="map " * (i * 100),
            )
            assert _estimate_tokens(result) <= 5000
