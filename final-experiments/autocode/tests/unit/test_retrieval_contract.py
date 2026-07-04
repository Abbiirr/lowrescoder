"""Tests for LanceDB/retrieval dependency contract (PLAN.md Section 1.2)."""

from autocode.layer2.embeddings import (
    RETRIEVAL_TIER_DESCRIPTIONS,
    RetrievalTier,
    _check_lancedb,
    _check_sentence_transformers,
    check_retrieval_tier,
)


class TestRetrievalTier:
    """Test the RetrievalTier enum."""

    def test_all_tiers_defined(self) -> None:
        """All three tiers are defined."""
        tiers = list(RetrievalTier)
        assert len(tiers) == 3
        assert RetrievalTier.BM25_ONLY in tiers
        assert RetrievalTier.HYBRID_IN_MEMORY in tiers
        assert RetrievalTier.HYBRID_PERSISTENT in tiers


class TestCheckFunctions:
    """Test individual dependency checks."""

    def test_sentence_transformers_check(self) -> None:
        """_check_sentence_transformers returns bool."""
        result = _check_sentence_transformers()
        assert isinstance(result, bool)

    def test_lancedb_check(self) -> None:
        """_check_lancedb returns bool."""
        result = _check_lancedb()
        assert isinstance(result, bool)


class TestCheckRetrievalTier:
    """Test the tier detection logic."""

    def test_bm25_only_when_no_embeddings(self) -> None:
        """BM25_ONLY when sentence-transformers unavailable."""
        from unittest.mock import patch

        with patch(
            "autocode.layer2.embeddings._check_sentence_transformers",
            return_value=False,
        ):
            tier = check_retrieval_tier()
            assert tier == RetrievalTier.BM25_ONLY

    def test_hybrid_in_memory_when_no_lancedb(self) -> None:
        """HYBRID_IN_MEMORY when embeddings but no LanceDB."""
        from unittest.mock import patch

        with (
            patch(
                "autocode.layer2.embeddings._check_sentence_transformers",
                return_value=True,
            ),
            patch(
                "autocode.layer2.embeddings._check_lancedb",
                return_value=False,
            ),
        ):
            tier = check_retrieval_tier()
            assert tier == RetrievalTier.HYBRID_IN_MEMORY

    def test_hybrid_persistent_when_both(self) -> None:
        """HYBRID_PERSISTENT when both available."""
        from unittest.mock import patch

        with (
            patch(
                "autocode.layer2.embeddings._check_sentence_transformers",
                return_value=True,
            ),
            patch(
                "autocode.layer2.embeddings._check_lancedb",
                return_value=True,
            ),
        ):
            tier = check_retrieval_tier()
            assert tier == RetrievalTier.HYBRID_PERSISTENT


class TestTierDescriptions:
    """Test tier description strings."""

    def test_all_tiers_have_descriptions(self) -> None:
        """Every tier has a human-readable description."""
        for tier in RetrievalTier:
            assert tier in RETRIEVAL_TIER_DESCRIPTIONS
            assert len(RETRIEVAL_TIER_DESCRIPTIONS[tier]) > 10

    def test_bm25_only_mentions_install(self) -> None:
        """BM25_ONLY description mentions install guidance."""
        desc = RETRIEVAL_TIER_DESCRIPTIONS[RetrievalTier.BM25_ONLY]
        assert "sentence-transformers" in desc
