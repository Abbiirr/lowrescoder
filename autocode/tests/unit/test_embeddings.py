"""Tests for the embedding engine (Sprint 3D)."""

from __future__ import annotations

from autocode.layer2.embeddings import BM25, EmbeddingEngine


class TestEmbeddingEngine:
    """Test the embedding engine with lazy loading and fallback."""

    def test_engine_creation(self):
        engine = EmbeddingEngine()
        assert engine._model is None  # Not loaded yet

    def test_unavailable_fallback(self):
        """When model is unavailable, embed should return empty vectors."""
        engine = EmbeddingEngine(model_name="nonexistent/model")
        # Force availability check
        result = engine.embed(["hello world"])
        assert len(result) == 1
        assert result[0] == []  # Empty embedding

    def test_embed_empty_list(self):
        engine = EmbeddingEngine()
        result = engine.embed([])
        assert result == []

    def test_embed_query_fallback(self):
        engine = EmbeddingEngine(model_name="nonexistent/model")
        result = engine.embed_query("test query")
        assert result == []

    def test_available_property(self):
        engine = EmbeddingEngine(model_name="nonexistent/model")
        assert engine.available is False


class TestBM25:
    """Test the BM25 implementation."""

    def test_index_and_search(self):
        bm25 = BM25()
        docs = [
            "def parse_file(path): return open(path).read()",
            "class UserManager: manages user accounts",
            "import os; import sys; from pathlib import Path",
        ]
        bm25.index(docs)
        results = bm25.search("parse file")
        assert len(results) > 0
        assert results[0][0] == 0  # First doc should match best

    def test_search_empty_index(self):
        bm25 = BM25()
        bm25.index([])
        results = bm25.search("anything")
        assert results == []

    def test_search_no_match(self):
        bm25 = BM25()
        bm25.index(["alpha beta gamma"])
        results = bm25.search("zzzzz")
        assert results == []

    def test_search_ranking(self):
        bm25 = BM25()
        docs = [
            "the cat sat on the mat",
            "the dog chased the cat",
            "the bird flew over the tree",
        ]
        bm25.index(docs)
        results = bm25.search("cat", top_k=3)
        # Both docs with "cat" should rank above the one without
        matched_indices = {r[0] for r in results}
        assert 0 in matched_indices
        assert 1 in matched_indices

    def test_camel_case_tokenization(self):
        bm25 = BM25()
        docs = ["def parseFileContent(): pass"]
        bm25.index(docs)
        results = bm25.search("parse file")
        assert len(results) > 0

    def test_snake_case_tokenization(self):
        bm25 = BM25()
        docs = ["def parse_file_content(): pass"]
        bm25.index(docs)
        results = bm25.search("parse file")
        assert len(results) > 0

    def test_top_k_limit(self):
        bm25 = BM25()
        docs = [f"document {i} with term" for i in range(20)]
        bm25.index(docs)
        results = bm25.search("term", top_k=5)
        assert len(results) <= 5

    def test_scores_are_positive(self):
        bm25 = BM25()
        docs = ["hello world", "world peace"]
        bm25.index(docs)
        results = bm25.search("world")
        for _, score in results:
            assert score > 0
