"""Benchmark: Search precision@3 for 10 known-answer queries (Gate 2).

Target: > 60% precision@3.
"""

from __future__ import annotations

import textwrap

import pytest

pytestmark = pytest.mark.benchmark


# --- Sample project files ---

PROJECT_FILES = {
    "src/parser.py": textwrap.dedent("""\
        import os
        from pathlib import Path

        class TreeSitterParser:
            def __init__(self, max_entries=500):
                self.cache = {}
                self.max_entries = max_entries

            def parse(self, file_path):
                source = Path(file_path).read_bytes()
                return self._do_parse(source)

            def _do_parse(self, source):
                return source

            def clear_cache(self):
                self.cache.clear()
    """),
    "src/router.py": textwrap.dedent("""\
        import re

        class RequestRouter:
            def classify(self, message):
                if 'list' in message:
                    return 'deterministic'
                return 'complex'

            def _match_patterns(self, message, patterns):
                for pattern in patterns:
                    if re.search(pattern, message):
                        return True
                return False
    """),
    "src/search.py": textwrap.dedent("""\
        class HybridSearch:
            def __init__(self, index, embeddings=None):
                self.index = index
                self.embeddings = embeddings

            def search(self, query, top_k=10):
                results = self._bm25_search(query)
                return results[:top_k]

            def _bm25_search(self, query):
                return []
    """),
    "src/config.py": textwrap.dedent("""\
        import yaml
        from pathlib import Path

        class Config:
            def __init__(self):
                self.model = "qwen3:8b"
                self.provider = "ollama"

            def load(self, path):
                with open(path) as f:
                    data = yaml.safe_load(f)
                return data

            def save(self, path, data):
                with open(path, 'w') as f:
                    yaml.dump(data, f)
    """),
    "src/tools.py": textwrap.dedent("""\
        class ToolRegistry:
            def __init__(self):
                self._tools = {}

            def register(self, name, handler):
                self._tools[name] = handler

            def get(self, name):
                return self._tools.get(name)

            def list_tools(self):
                return list(self._tools.keys())
    """),
    "tests/test_parser.py": textwrap.dedent("""\
        import pytest
        from src.parser import TreeSitterParser

        def test_parse_file(tmp_path):
            parser = TreeSitterParser()
            f = tmp_path / "test.py"
            f.write_text("x = 1")
            result = parser.parse(str(f))
            assert result is not None

        def test_cache_clear():
            parser = TreeSitterParser()
            parser.clear_cache()
            assert parser.cache == {}
    """),
}


# Known-answer queries: (query, expected_file_keywords)
KNOWN_ANSWER_QUERIES = [
    ("parse file", ["parser"]),
    ("router classify", ["router"]),
    ("search query", ["search"]),
    ("config load yaml", ["config"]),
    ("tool registry register", ["tools"]),
    ("cache clear", ["parser"]),
    ("bm25 search", ["search"]),
    ("pattern matching", ["router"]),
    ("test parser", ["test_parser"]),
    ("list tools", ["tools"]),
]


@pytest.fixture
def indexed_project(tmp_path):
    """Create and index a sample project."""
    for rel_path, content in PROJECT_FILES.items():
        path = tmp_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    from autocode.layer2.index import CodeIndex

    index = CodeIndex()
    index.build(tmp_path)
    return index, tmp_path


class TestSearchRelevance:
    """Test precision@3 for known-answer queries."""

    def _precision_at_k(
        self, results, expected_keywords, k=3,
    ) -> float:
        """Compute precision@k: fraction of top-k results containing expected keywords."""
        top_results = results[:k]
        if not top_results:
            return 0.0

        hits = 0
        for result in top_results:
            file_path = result.chunk.file_path.lower()
            content = result.chunk.content.lower()
            for kw in expected_keywords:
                if kw.lower() in file_path or kw.lower() in content:
                    hits += 1
                    break

        return hits / len(top_results)

    def test_precision_at_3_overall(self, indexed_project):
        """Overall precision@3 should be > 60%."""
        from autocode.layer2.embeddings import EmbeddingEngine
        from autocode.layer2.search import HybridSearch

        index, _ = indexed_project
        engine = EmbeddingEngine(model_name="nonexistent/model")  # BM25-only
        search = HybridSearch(index, embeddings=engine)

        total_precision = 0.0
        passing = 0

        for query, expected_kw in KNOWN_ANSWER_QUERIES:
            results = search.search(query, top_k=3)
            p = self._precision_at_k(results, expected_kw, k=3)
            total_precision += p
            if p > 0:
                passing += 1

        avg_precision = total_precision / len(KNOWN_ANSWER_QUERIES)
        assert avg_precision > 0.6, (
            f"Average precision@3 = {avg_precision:.2f} (target > 0.6). "
            f"{passing}/{len(KNOWN_ANSWER_QUERIES)} queries had hits."
        )

    def test_parse_file_query(self, indexed_project):
        from autocode.layer2.embeddings import EmbeddingEngine
        from autocode.layer2.search import HybridSearch

        index, _ = indexed_project
        search = HybridSearch(index, embeddings=EmbeddingEngine(model_name="none"))
        results = search.search("parse file", top_k=3)
        assert len(results) > 0

    def test_config_query(self, indexed_project):
        from autocode.layer2.embeddings import EmbeddingEngine
        from autocode.layer2.search import HybridSearch

        index, _ = indexed_project
        search = HybridSearch(index, embeddings=EmbeddingEngine(model_name="none"))
        results = search.search("config load yaml", top_k=3)
        assert len(results) > 0

    def test_tool_registry_query(self, indexed_project):
        from autocode.layer2.embeddings import EmbeddingEngine
        from autocode.layer2.search import HybridSearch

        index, _ = indexed_project
        search = HybridSearch(index, embeddings=EmbeddingEngine(model_name="none"))
        results = search.search("tool registry register", top_k=3)
        assert len(results) > 0

    def test_router_query(self, indexed_project):
        from autocode.layer2.embeddings import EmbeddingEngine
        from autocode.layer2.search import HybridSearch

        index, _ = indexed_project
        search = HybridSearch(index, embeddings=EmbeddingEngine(model_name="none"))
        results = search.search("router classify message", top_k=3)
        assert len(results) > 0

    def test_search_query(self, indexed_project):
        from autocode.layer2.embeddings import EmbeddingEngine
        from autocode.layer2.search import HybridSearch

        index, _ = indexed_project
        search = HybridSearch(index, embeddings=EmbeddingEngine(model_name="none"))
        results = search.search("search query results", top_k=3)
        assert len(results) > 0

    def test_bm25_fallback_works(self, indexed_project):
        """Search should work when embedding model is unavailable."""
        from autocode.layer2.embeddings import EmbeddingEngine
        from autocode.layer2.search import HybridSearch

        index, _ = indexed_project
        engine = EmbeddingEngine(model_name="nonexistent/model")
        assert not engine.available

        search = HybridSearch(index, embeddings=engine)
        results = search.search("parse file", top_k=3)
        assert len(results) > 0
        assert all(r.match_type == "bm25" for r in results)

    def test_cache_clear_query(self, indexed_project):
        from autocode.layer2.embeddings import EmbeddingEngine
        from autocode.layer2.search import HybridSearch

        index, _ = indexed_project
        search = HybridSearch(index, embeddings=EmbeddingEngine(model_name="none"))
        results = search.search("cache clear", top_k=3)
        assert len(results) > 0

    def test_test_parser_query(self, indexed_project):
        from autocode.layer2.embeddings import EmbeddingEngine
        from autocode.layer2.search import HybridSearch

        index, _ = indexed_project
        search = HybridSearch(index, embeddings=EmbeddingEngine(model_name="none"))
        results = search.search("test parser", top_k=3)
        assert len(results) > 0

    def test_list_tools_query(self, indexed_project):
        from autocode.layer2.embeddings import EmbeddingEngine
        from autocode.layer2.search import HybridSearch

        index, _ = indexed_project
        search = HybridSearch(index, embeddings=EmbeddingEngine(model_name="none"))
        results = search.search("list tools", top_k=3)
        assert len(results) > 0
