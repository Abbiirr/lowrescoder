"""Tests for the code index (Sprint 3E)."""

from __future__ import annotations

import textwrap

import pytest

ts_available = True
try:
    import tree_sitter  # noqa: F401
    import tree_sitter_python  # noqa: F401

    from hybridcoder.config import Layer2Config
    from hybridcoder.layer2.index import (
        CodeIndex,
        _load_gitignore_patterns,
        _should_ignore,
    )
except ImportError:
    ts_available = False

pytestmark = pytest.mark.skipif(not ts_available, reason="tree-sitter not installed")

SAMPLE_PY = textwrap.dedent("""\
    import os

    def hello():
        return "hello"

    class Greeter:
        def greet(self, name):
            return f"Hello, {name}"
""")


class TestCodeIndex:
    def test_build_empty_project(self, tmp_path):
        index = CodeIndex()
        stats = index.build(tmp_path)
        assert stats["files_scanned"] == 0
        assert stats["chunks_created"] == 0
        assert index.chunk_count == 0

    def test_build_with_python_files(self, tmp_path):
        (tmp_path / "main.py").write_text(SAMPLE_PY)
        (tmp_path / "utils.py").write_text("def util(): pass")

        index = CodeIndex()
        stats = index.build(tmp_path)
        assert stats["files_scanned"] == 2
        assert stats["files_indexed"] == 2
        assert stats["chunks_created"] > 0
        assert index.chunk_count > 0
        assert index.file_count == 2

    def test_incremental_update(self, tmp_path):
        (tmp_path / "main.py").write_text(SAMPLE_PY)

        index = CodeIndex()
        stats1 = index.build(tmp_path)
        initial_chunks = stats1["chunks_created"]

        # Second build with no changes
        stats2 = index.build(tmp_path)
        assert stats2["files_indexed"] == 0, "No files should be re-indexed"
        assert index.chunk_count == initial_chunks

    def test_incremental_reindex_changed_file(self, tmp_path):
        f = tmp_path / "main.py"
        f.write_text("def old(): pass")

        index = CodeIndex()
        index.build(tmp_path)

        f.write_text("def new_function(): pass\ndef another(): pass")
        stats = index.build(tmp_path)
        assert stats["files_indexed"] == 1

    def test_gitignore_filtering(self, tmp_path):
        (tmp_path / ".gitignore").write_text("*.pyc\n__pycache__/\nbuild/\n")
        (tmp_path / "main.py").write_text(SAMPLE_PY)

        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "cached.py").write_text("x = 1")

        index = CodeIndex()
        stats = index.build(tmp_path)
        assert stats["files_scanned"] == 1  # Only main.py

    def test_max_files_cap(self, tmp_path):
        for i in range(10):
            (tmp_path / f"file{i}.py").write_text(f"x = {i}")

        config = Layer2Config(max_files=3)
        index = CodeIndex(config=config)
        stats = index.build(tmp_path)
        assert stats["files_scanned"] <= 3

    def test_get_chunks(self, tmp_path):
        (tmp_path / "main.py").write_text(SAMPLE_PY)
        index = CodeIndex()
        index.build(tmp_path)
        chunks = index.get_chunks()
        assert len(chunks) > 0
        assert all(hasattr(c, "content") for c in chunks)

    def test_deleted_file_cleanup(self, tmp_path):
        f = tmp_path / "temp.py"
        f.write_text("def temp(): pass")

        index = CodeIndex()
        index.build(tmp_path)
        assert index.file_count == 1

        f.unlink()
        index.build(tmp_path)
        assert index.file_count == 0

    def test_build_stats_time(self, tmp_path):
        (tmp_path / "main.py").write_text(SAMPLE_PY)
        index = CodeIndex()
        stats = index.build(tmp_path)
        assert stats["time_ms"] >= 0

    def test_nested_directories(self, tmp_path):
        sub = tmp_path / "src" / "pkg"
        sub.mkdir(parents=True)
        (sub / "mod.py").write_text("def func(): pass")

        index = CodeIndex()
        stats = index.build(tmp_path)
        assert stats["files_scanned"] >= 1

    def test_non_python_files_ignored(self, tmp_path):
        (tmp_path / "main.py").write_text(SAMPLE_PY)
        (tmp_path / "readme.md").write_text("# Hello")
        (tmp_path / "config.yaml").write_text("key: value")

        index = CodeIndex()
        stats = index.build(tmp_path)
        assert stats["files_scanned"] == 1

    def test_build_returns_total_chunks(self, tmp_path):
        (tmp_path / "a.py").write_text("def a(): pass")
        (tmp_path / "b.py").write_text("def b(): pass")

        index = CodeIndex()
        stats = index.build(tmp_path)
        assert stats["total_chunks"] == index.chunk_count


class TestGitignoreHelpers:
    def test_should_ignore_pycache(self, tmp_path):
        patterns = ["__pycache__"]
        path = tmp_path / "__pycache__" / "foo.py"
        assert _should_ignore(path, tmp_path, patterns)

    def test_should_not_ignore_normal_file(self, tmp_path):
        patterns = ["__pycache__"]
        path = tmp_path / "main.py"
        assert not _should_ignore(path, tmp_path, patterns)

    def test_load_gitignore_default_patterns(self, tmp_path):
        patterns = _load_gitignore_patterns(tmp_path)
        assert ".git" in patterns
        assert "__pycache__" in patterns
