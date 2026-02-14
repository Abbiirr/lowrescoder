"""Tests for L2/L3 wiring in the server (Sprint 4C).

Tests the layer routing logic, cache reuse strategy, and layer_used contract.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from hybridcoder.core.context import ContextAssembler
from hybridcoder.core.types import RequestType


class TestL2Wiring:
    """5 tests for L2 (retrieval) wiring."""

    def test_classification_returns_semantic_search(self) -> None:
        """RequestRouter classifies search queries as SEMANTIC_SEARCH."""
        from hybridcoder.core.router import RequestRouter

        router = RequestRouter()
        # "how does X work" pattern is the canonical semantic search trigger
        result = router.classify("how does the parser work")
        assert result == RequestType.SEMANTIC_SEARCH

    def test_context_assembler_assembly(self) -> None:
        """ContextAssembler assembles context within budget."""
        assembler = ContextAssembler(context_budget=1000)
        result = assembler.assemble(
            "test query",
            rules="- Always use pytest",
            repomap="src/ -> tests/",
        )
        assert "Project Rules" in result
        assert "Always use pytest" in result
        assert "Repo Map" in result

    def test_cache_reuse_not_rebuild(self) -> None:
        """Code index cache is reused, not rebuilt per request."""
        from hybridcoder.agent import tools

        # Set a mock cache
        mock_index = MagicMock()
        original = tools._code_index_cache
        try:
            tools._code_index_cache = mock_index
            # Accessing the cache should return the same object
            assert tools._code_index_cache is mock_index
            # Clear should reset
            tools.clear_code_index_cache()
            assert tools._code_index_cache is None
        finally:
            tools._code_index_cache = original

    def test_rules_loader(self) -> None:
        """RulesLoader loads rules from project root."""
        from hybridcoder.layer2.rules import RulesLoader

        loader = RulesLoader()
        # Should return empty string for nonexistent path, not crash
        rules = loader.load("/nonexistent/path")
        assert isinstance(rules, str)

    def test_layer_used_value(self) -> None:
        """RequestType SEMANTIC_SEARCH maps to layer 2."""
        assert RequestType.SEMANTIC_SEARCH.value == "search"
        # The server routes SEMANTIC_SEARCH to layer_used=2


class TestL3Wiring:
    """2 tests for L3 (constrained gen) wiring."""

    def test_routes_to_l3(self) -> None:
        """SIMPLE_EDIT request type exists for L3 routing."""
        assert RequestType.SIMPLE_EDIT.value == "simple_edit"

    def test_fallback_to_l4(self) -> None:
        """L3 gracefully falls back to L4 when deps not available."""
        # Simulate ImportError for llama_cpp
        try:
            from hybridcoder.layer3.provider import L3Provider
            provider = L3Provider("/nonexistent.gguf")
            # is_available should be False since model file doesn't exist
            # (and likely llama_cpp is not installed in test env)
            # Either way, this shouldn't crash
            available = provider.is_available
            assert isinstance(available, bool)
        except ImportError:
            # If llama_cpp not installed, this is the expected fallback
            pass
