"""Tests for hybrid search (Sprint 3E)."""

from __future__ import annotations

import textwrap

import pytest

from autocode.core.types import SearchResult
from autocode.layer2.embeddings import EmbeddingEngine
from autocode.layer2.index import CodeIndex
from autocode.layer2.search import HybridSearch

SAMPLE_FILES = {
    "parser.py": textwrap.dedent("""\
        def parse_file(path):
            with open(path) as f:
                return f.read()

        def parse_string(source):
            return source.strip()
    """),
    "search.py": textwrap.dedent("""\
        def search_text(query, documents):
            results = []
            for doc in documents:
                if query in doc:
                    results.append(doc)
            return results
    """),
    "utils.py": textwrap.dedent("""\
        import os
        from pathlib import Path

        def read_config(path):
            return Path(path).read_text()

        def ensure_dir(path):
            os.makedirs(path, exist_ok=True)
    """),
}


@pytest.fixture
def indexed_project(tmp_path):
    """Create a sample project and build the index."""
    for name, content in SAMPLE_FILES.items():
        (tmp_path / name).write_text(content)

    index = CodeIndex()
    index.build(tmp_path)
    return index


class TestHybridSearch:
    def test_bm25_search(self, indexed_project):
        """BM25-only search should work without embeddings."""
        engine = EmbeddingEngine(model_name="nonexistent/model")
        search = HybridSearch(indexed_project, embeddings=engine)
        results = search.search("parse file")
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)

    def test_bm25_match_type(self, indexed_project):
        engine = EmbeddingEngine(model_name="nonexistent/model")
        search = HybridSearch(indexed_project, embeddings=engine)
        results = search.search("parse")
        assert all(r.match_type == "bm25" for r in results)

    def test_search_ranking(self, indexed_project):
        """Results should be ranked by relevance."""
        engine = EmbeddingEngine(model_name="nonexistent/model")
        search = HybridSearch(indexed_project, embeddings=engine)
        results = search.search("parse file path")
        if len(results) >= 2:
            assert results[0].score >= results[1].score

    def test_search_empty_query(self, indexed_project):
        engine = EmbeddingEngine(model_name="nonexistent/model")
        search = HybridSearch(indexed_project, embeddings=engine)
        results = search.search("")
        # Empty query may return empty or all results depending on BM25
        assert isinstance(results, list)

    def test_search_no_match(self, indexed_project):
        engine = EmbeddingEngine(model_name="nonexistent/model")
        search = HybridSearch(indexed_project, embeddings=engine)
        results = search.search("zzzznonexistentzzz")
        assert results == []

    def test_top_k_limit(self, indexed_project):
        engine = EmbeddingEngine(model_name="nonexistent/model")
        search = HybridSearch(indexed_project, embeddings=engine)
        results = search.search("def", top_k=2)
        assert len(results) <= 2

    def test_search_empty_index(self):
        index = CodeIndex()
        engine = EmbeddingEngine(model_name="nonexistent/model")
        search = HybridSearch(index, embeddings=engine)
        results = search.search("anything")
        assert results == []

    def test_result_has_chunk(self, indexed_project):
        engine = EmbeddingEngine(model_name="nonexistent/model")
        search = HybridSearch(indexed_project, embeddings=engine)
        results = search.search("search text")
        for r in results:
            assert r.chunk is not None
            assert r.chunk.content

    def test_result_score_positive(self, indexed_project):
        engine = EmbeddingEngine(model_name="nonexistent/model")
        search = HybridSearch(indexed_project, embeddings=engine)
        results = search.search("parse")
        for r in results:
            assert r.score > 0

    def test_rrf_weight(self, indexed_project):
        """Different hybrid weights should produce valid results."""
        engine = EmbeddingEngine(model_name="nonexistent/model")
        search = HybridSearch(indexed_project, embeddings=engine, hybrid_weight=0.8)
        results = search.search("parse")
        assert isinstance(results, list)

    def test_search_config_text(self, indexed_project):
        """Search for configuration-related code."""
        engine = EmbeddingEngine(model_name="nonexistent/model")
        search = HybridSearch(indexed_project, embeddings=engine)
        results = search.search("read config path")
        assert len(results) > 0

    def test_multiple_searches(self, indexed_project):
        """Multiple searches should work on the same index."""
        engine = EmbeddingEngine(model_name="nonexistent/model")
        search = HybridSearch(indexed_project, embeddings=engine)

        r1 = search.search("parse")
        r2 = search.search("search")
        r3 = search.search("config")

        assert len(r1) > 0
        assert len(r2) > 0
        assert len(r3) > 0
