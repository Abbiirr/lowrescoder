"""Embedding engine for code search.

Wraps jina-v2-base-code (768-dim) with lazy loading and CPU-only support.
Falls back to BM25-only when the embedding model is unavailable.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """Generate embeddings for code chunks using sentence-transformers.

    The model is loaded lazily on first use to preserve GPU VRAM for the LLM.
    When sentence-transformers is not installed or the model fails to load,
    the engine degrades to BM25-only mode (still functional for search).
    """

    def __init__(
        self,
        model_name: str = "jinaai/jina-embeddings-v2-base-code",
        device: str = "cpu",
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._model: object | None = None
        self._available: bool | None = None  # None = not yet checked

    @property
    def available(self) -> bool:
        """Whether embedding model is available (lazy check)."""
        if self._available is None:
            self._try_load()
        return bool(self._available)

    def _try_load(self) -> None:
        """Attempt to load the sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                self._model_name,
                device=self._device,
                trust_remote_code=True,
            )
            self._available = True
            logger.info("Loaded embedding model: %s", self._model_name)
        except Exception as e:
            self._available = False
            logger.warning(
                "Embedding model unavailable (%s), falling back to BM25-only: %s",
                self._model_name, e,
            )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of code/text strings to embed.

        Returns:
            List of embedding vectors. Returns empty list of vectors
            if the model is unavailable.
        """
        if not texts:
            return []

        if not self.available or self._model is None:
            return [[] for _ in texts]

        embeddings = self._model.encode(  # type: ignore[attr-defined]
            texts,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return [emb.tolist() for emb in embeddings]

    def embed_query(self, query: str) -> list[float]:
        """Generate an embedding for a single search query.

        Args:
            query: The search query string.

        Returns:
            Embedding vector, or empty list if unavailable.
        """
        results = self.embed([query])
        return results[0] if results else []


class BM25:
    """Simple BM25 implementation for keyword-based code search.

    Used as the primary search method when embeddings are unavailable,
    and as part of hybrid search when they are.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self._k1 = k1
        self._b = b
        self._docs: list[list[str]] = []
        self._doc_count = 0
        self._avg_dl = 0.0
        self._df: Counter[str] = Counter()

    def index(self, documents: list[str]) -> None:
        """Index a list of documents for BM25 search.

        Args:
            documents: List of text documents to index.
        """
        self._docs = [self._tokenize(doc) for doc in documents]
        self._doc_count = len(self._docs)
        if self._doc_count == 0:
            self._avg_dl = 0.0
            return

        total_len = sum(len(d) for d in self._docs)
        self._avg_dl = total_len / self._doc_count

        self._df = Counter()
        for doc in self._docs:
            unique_terms = set(doc)
            for term in unique_terms:
                self._df[term] += 1

    def search(self, query: str, top_k: int = 10) -> list[tuple[int, float]]:
        """Search indexed documents.

        Args:
            query: Search query string.
            top_k: Number of results to return.

        Returns:
            List of (doc_index, score) tuples, sorted by score descending.
        """
        if not self._docs:
            return []

        query_terms = self._tokenize(query)
        scores: list[tuple[int, float]] = []

        for i, doc in enumerate(self._docs):
            score = self._score_doc(query_terms, doc)
            if score > 0:
                scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _score_doc(self, query_terms: list[str], doc: list[str]) -> float:
        """Compute BM25 score for a single document."""
        doc_len = len(doc)
        if doc_len == 0:
            return 0.0

        tf = Counter(doc)
        score = 0.0

        for term in query_terms:
            if term not in tf:
                continue

            term_freq = tf[term]
            doc_freq = self._df.get(term, 0)

            # IDF component
            idf = math.log(
                (self._doc_count - doc_freq + 0.5) / (doc_freq + 0.5) + 1,
            )

            # TF component with length normalization
            tf_norm = (term_freq * (self._k1 + 1)) / (
                term_freq + self._k1 * (1 - self._b + self._b * doc_len / max(self._avg_dl, 1))
            )

            score += idf * tf_norm

        return score

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into lowercase terms."""
        # Split on non-alphanumeric, also split camelCase and snake_case
        text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
        text = text.replace("_", " ").replace("-", " ")
        tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
        return tokens
