"""Hybrid search combining BM25 + vector search with Reciprocal Rank Fusion."""

from __future__ import annotations

from hybridcoder.core.types import CodeChunk, SearchResult
from hybridcoder.layer2.embeddings import BM25, EmbeddingEngine
from hybridcoder.layer2.index import CodeIndex


class HybridSearch:
    """BM25 + vector search with Reciprocal Rank Fusion (RRF).

    When embeddings are unavailable, degrades to BM25-only search.
    """

    def __init__(
        self,
        index: CodeIndex,
        embeddings: EmbeddingEngine | None = None,
        rrf_k: int = 60,
        hybrid_weight: float = 0.5,
    ) -> None:
        """Initialize hybrid search.

        Args:
            index: The code index to search.
            embeddings: Embedding engine for vector search.
            rrf_k: RRF constant (default 60).
            hybrid_weight: Weight for vector vs BM25 (0.0 = BM25 only, 1.0 = vector only).
        """
        self._index = index
        self._embeddings = embeddings or EmbeddingEngine()
        self._rrf_k = rrf_k
        self._hybrid_weight = hybrid_weight
        self._bm25 = BM25()
        self._bm25_indexed = False

    def _ensure_bm25(self) -> None:
        """Build BM25 index from current chunks if not already done."""
        chunks = self._index.get_chunks()
        if not self._bm25_indexed or len(chunks) != self._bm25._doc_count:
            self._bm25.index([c.content for c in chunks])
            self._bm25_indexed = True

    def search(self, query: str, top_k: int = 10) -> list[SearchResult]:
        """Search for code chunks matching the query.

        Uses BM25 + vector search with RRF fusion when embeddings are
        available, falls back to BM25-only otherwise.

        Args:
            query: Search query string.
            top_k: Number of results to return.

        Returns:
            List of SearchResult objects sorted by relevance score.
        """
        chunks = self._index.get_chunks()
        if not chunks:
            return []

        self._ensure_bm25()

        # BM25 search
        bm25_results = self._bm25.search(query, top_k=top_k * 2)
        bm25_ranks: dict[int, int] = {
            doc_idx: rank for rank, (doc_idx, _) in enumerate(bm25_results)
        }

        # Vector search (if available)
        vector_ranks: dict[int, int] = {}
        if self._embeddings.available:
            query_embedding = self._embeddings.embed_query(query)
            if query_embedding:
                vector_results = self._vector_search(chunks, query_embedding, top_k * 2)
                vector_ranks = {
                    doc_idx: rank for rank, (doc_idx, _) in enumerate(vector_results)
                }

        # RRF fusion
        if vector_ranks:
            fused = self._rrf_fuse(bm25_ranks, vector_ranks)
            match_type = "hybrid"
        else:
            fused = [(idx, 1.0 / (self._rrf_k + rank)) for idx, rank in bm25_ranks.items()]
            fused.sort(key=lambda x: x[1], reverse=True)
            match_type = "bm25"

        # Build results
        results: list[SearchResult] = []
        for doc_idx, score in fused[:top_k]:
            if 0 <= doc_idx < len(chunks):
                results.append(SearchResult(
                    chunk=chunks[doc_idx],
                    score=score,
                    match_type=match_type,
                ))

        return results

    def _vector_search(
        self,
        chunks: list[CodeChunk],
        query_embedding: list[float],
        top_k: int,
    ) -> list[tuple[int, float]]:
        """Compute cosine similarity between query and chunk embeddings."""
        results: list[tuple[int, float]] = []

        for i, chunk in enumerate(chunks):
            if not chunk.embedding:
                continue
            sim = self._cosine_similarity(query_embedding, chunk.embedding)
            results.append((i, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b) or not a:
            return 0.0

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)  # type: ignore[no-any-return]

    def _rrf_fuse(
        self,
        bm25_ranks: dict[int, int],
        vector_ranks: dict[int, int],
    ) -> list[tuple[int, float]]:
        """Reciprocal Rank Fusion of BM25 and vector rankings.

        Score = w_bm25 / (k + rank_bm25) + w_vec / (k + rank_vec)
        where w_bm25 = 1 - hybrid_weight, w_vec = hybrid_weight.
        """
        k = self._rrf_k
        w_bm25 = 1.0 - self._hybrid_weight
        w_vec = self._hybrid_weight

        all_docs = set(bm25_ranks.keys()) | set(vector_ranks.keys())
        scores: list[tuple[int, float]] = []

        for doc_idx in all_docs:
            score = 0.0
            if doc_idx in bm25_ranks:
                score += w_bm25 / (k + bm25_ranks[doc_idx])
            if doc_idx in vector_ranks:
                score += w_vec / (k + vector_ranks[doc_idx])
            scores.append((doc_idx, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores
