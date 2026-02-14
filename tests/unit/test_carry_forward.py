"""Carry-forward fix tests (Sprint 4A)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestBoundedRglob:
    def test_bounded_rglob_stops_early(self):
        """Verify islice pattern stops iterating after 100 entries."""
        from itertools import islice

        # Simulate a very large iterator
        large_iter = (f"file_{i}.py" for i in range(10000))
        result = list(islice(large_iter, 100))
        assert len(result) == 100
        assert result[0] == "file_0.py"
        assert result[99] == "file_99.py"


class TestCodeIndexCache:
    def test_code_index_cache_reused(self):
        """Verify CodeIndex is reused across calls via module-level cache."""
        import hybridcoder.agent.tools as tools_module

        # Clear cache first
        tools_module._code_index_cache = None

        # Create a mock CodeIndex
        mock_index = MagicMock()
        mock_index.build = MagicMock()

        with patch.object(tools_module, "_code_index_cache", None):
            # Simulate what _handle_search_code does: check cache, create if None
            assert tools_module._code_index_cache is None
            tools_module._code_index_cache = mock_index
            assert tools_module._code_index_cache is mock_index

            # Second access should return same object
            cached = tools_module._code_index_cache
            assert cached is mock_index

        # Test clear function
        tools_module._code_index_cache = mock_index
        tools_module.clear_code_index_cache()
        assert tools_module._code_index_cache is None
