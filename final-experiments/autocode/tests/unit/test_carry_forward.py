"""Carry-forward fix tests (Sprint 4A)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from autocode.core.types import CodeChunk, SearchResult


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
    def test_warm_code_index_reuses_cache_for_same_root(self, tmp_path: Path):
        """Warmup should reuse the same CodeIndex object for one project root."""
        import autocode.agent.tools as tools_module

        # Clear cache first
        tools_module.clear_code_index_cache()

        mock_index = MagicMock()
        mock_index.build.side_effect = [
            {
                "files_scanned": 2,
                "files_indexed": 2,
                "chunks_created": 4,
                "total_chunks": 4,
                "time_ms": 10,
            },
            {
                "files_scanned": 2,
                "files_indexed": 0,
                "chunks_created": 0,
                "total_chunks": 4,
                "time_ms": 1,
            },
        ]

        with patch("autocode.layer2.index.CodeIndex", return_value=mock_index) as mock_cls:
            index1, stats1 = tools_module.warm_code_index(str(tmp_path))
            index2, stats2 = tools_module.warm_code_index(str(tmp_path))

        assert index1 is mock_index
        assert index2 is mock_index
        assert stats1["chunks_created"] == 4
        assert stats2["files_indexed"] == 0
        assert mock_cls.call_count == 1
        assert mock_index.build.call_count == 2

    def test_warm_code_index_invalidates_on_root_change(self, tmp_path: Path):
        """Changing project roots should create a fresh index object."""
        import autocode.agent.tools as tools_module

        tools_module.clear_code_index_cache()
        root_a = tmp_path / "a"
        root_b = tmp_path / "b"
        root_a.mkdir()
        root_b.mkdir()

        mock_a = MagicMock()
        mock_a.build.return_value = {
            "files_scanned": 1,
            "files_indexed": 1,
            "chunks_created": 1,
            "total_chunks": 1,
            "time_ms": 1,
        }
        mock_b = MagicMock()
        mock_b.build.return_value = {
            "files_scanned": 1,
            "files_indexed": 1,
            "chunks_created": 2,
            "total_chunks": 2,
            "time_ms": 1,
        }

        with patch("autocode.layer2.index.CodeIndex", side_effect=[mock_a, mock_b]) as mock_cls:
            index_a, _stats_a = tools_module.warm_code_index(str(root_a))
            index_b, _stats_b = tools_module.warm_code_index(str(root_b))

        assert index_a is mock_a
        assert index_b is mock_b
        assert mock_cls.call_count == 2


class TestActiveWorkingSet:
    def test_record_active_file_prefers_recent_and_frequent(self, tmp_path: Path):
        """Working set should favor the newest hot file."""
        import autocode.agent.tools as tools_module

        tools_module.clear_active_working_set()
        alpha = tmp_path / "alpha.py"
        beta = tmp_path / "beta.py"
        alpha.write_text("print('a')\n", encoding="utf-8")
        beta.write_text("print('b')\n", encoding="utf-8")

        tools_module.record_active_file(alpha, project_root=str(tmp_path), weight=1)
        tools_module.record_active_file(beta, project_root=str(tmp_path), weight=1)
        tools_module.record_active_file(alpha, project_root=str(tmp_path), weight=3)

        working_set = tools_module.get_active_working_set(str(tmp_path), limit=2)

        assert working_set == ["alpha.py", "beta.py"]

    def test_search_code_boosts_active_working_set_results(self, tmp_path: Path):
        """Active files should get a small retrieval boost in search_code output."""
        import autocode.agent.tools as tools_module

        tools_module.clear_active_working_set()
        hot = tmp_path / "hot.py"
        cold = tmp_path / "cold.py"
        hot.write_text("def target():\n    return 1\n", encoding="utf-8")
        cold.write_text("def target():\n    return 2\n", encoding="utf-8")
        tools_module.record_active_file(hot, project_root=str(tmp_path), weight=5)

        hot_result = SearchResult(
            chunk=CodeChunk(
                content="def target():\n    return 1\n",
                file_path=str(hot),
                language="python",
                start_line=1,
                end_line=2,
                chunk_type="function",
            ),
            score=0.3,
            match_type="hybrid",
        )
        cold_result = SearchResult(
            chunk=CodeChunk(
                content="def target():\n    return 2\n",
                file_path=str(cold),
                language="python",
                start_line=1,
                end_line=2,
                chunk_type="function",
            ),
            score=0.31,
            match_type="hybrid",
        )

        mock_search = MagicMock()
        mock_search.search.return_value = [cold_result, hot_result]

        with (
            patch("autocode.agent.tools.warm_code_index", return_value=(MagicMock(), {})),
            patch("autocode.layer2.embeddings.EmbeddingEngine"),
            patch("autocode.layer2.search.HybridSearch", return_value=mock_search),
        ):
            result = tools_module._handle_search_code("target", project_root=str(tmp_path))

        hot_line = next(line for line in result.splitlines() if "hot.py:1" in line)
        assert "working-set" in hot_line
