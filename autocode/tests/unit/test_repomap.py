"""Tests for the repo map generator (Sprint 3F)."""

from __future__ import annotations

import os
import textwrap

from autocode.layer2.repomap import RepoMapGenerator


class TestRepoMapGenerator:
    def test_default_budget_is_1000_tokens(self):
        """C4.G2 default repo-map budget should be 1000 tokens."""
        from autocode.config import Layer2Config

        assert Layer2Config().repomap_budget == 1000
        assert RepoMapGenerator().budget_tokens == 1000

    def test_generate_simple_project(self, tmp_path):
        (tmp_path / "main.py").write_text(textwrap.dedent("""\
            def hello():
                pass

            class Greeter:
                def greet(self):
                    pass
        """))

        gen = RepoMapGenerator()
        result = gen.generate(tmp_path)
        assert "# Repo Map" in result
        assert "hello" in result
        assert "Greeter" in result

    def test_budget_compliance(self, tmp_path):
        """Generated map should stay within token budget."""
        for i in range(20):
            (tmp_path / f"mod{i}.py").write_text(
                "\n".join(f"def func_{i}_{j}(): pass" for j in range(10))
            )

        gen = RepoMapGenerator(budget_tokens=200)
        result = gen.generate(tmp_path)
        # Budget is 200 tokens * 4 chars/token = 800 chars
        assert len(result) <= 200 * 4 + 50  # Small overhead for truncation message

    def test_empty_project(self, tmp_path):
        gen = RepoMapGenerator()
        result = gen.generate(tmp_path)
        assert "no Python files found" in result

    def test_symbol_ranking(self, tmp_path):
        (tmp_path / "code.py").write_text(textwrap.dedent("""\
            import os

            MAX = 100

            class MyClass:
                def method(self):
                    pass

            def function():
                pass
        """))

        gen = RepoMapGenerator()
        result = gen.generate(tmp_path)
        # Classes should appear before functions in the ranking
        class_pos = result.find("MyClass")
        func_pos = result.find("function")
        if class_pos >= 0 and func_pos >= 0:
            assert class_pos < func_pos, "Classes should be ranked before functions"

    def test_ignores_pycache(self, tmp_path):
        (tmp_path / "main.py").write_text("def func(): pass")
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "cached.py").write_text("def cached(): pass")

        gen = RepoMapGenerator()
        result = gen.generate(tmp_path)
        assert "cached" not in result

    def test_multiple_files(self, tmp_path):
        (tmp_path / "a.py").write_text("def alpha(): pass")
        (tmp_path / "b.py").write_text("def beta(): pass")

        gen = RepoMapGenerator()
        result = gen.generate(tmp_path)
        assert "alpha" in result
        assert "beta" in result

    def test_truncation_marker(self, tmp_path):
        """Large projects should show truncation marker."""
        for i in range(50):
            (tmp_path / f"mod{i}.py").write_text(
                "\n".join(f"def func_{i}_{j}(): pass" for j in range(20))
            )

        gen = RepoMapGenerator(budget_tokens=100)
        result = gen.generate(tmp_path)
        assert "truncated" in result

    def test_custom_budget(self, tmp_path):
        (tmp_path / "main.py").write_text("def func(): pass")
        gen = RepoMapGenerator(budget_tokens=50)
        result = gen.generate(tmp_path)
        assert len(result) <= 50 * 4 + 50

    def test_dependency_graph_ranking_respects_import_fan_in_under_budget(self, tmp_path):
        """Files imported by more files should survive tight budgets first."""
        (tmp_path / "a_consumer.py").write_text("from z_core import core\n")
        (tmp_path / "b_consumer.py").write_text("from z_core import core\n")
        (tmp_path / "c_leaf.py").write_text("def leaf_symbol():\n    return 'leaf'\n")
        (tmp_path / "z_core.py").write_text("def core_symbol():\n    return 'core'\n")

        gen = RepoMapGenerator(budget_tokens=28, cache_dir=tmp_path / ".cache")
        result = gen.generate(tmp_path)

        assert "z_core.py" in result
        assert "core_symbol" in result
        assert "c_leaf.py" not in result

    def test_disk_cache_invalidates_when_mtime_and_hash_change(self, tmp_path):
        """Persistent cache entries should be invalidated by mtime + sha changes."""
        source = tmp_path / "main.py"
        source.write_text("def first_symbol():\n    return 1\n")
        cache_dir = tmp_path / ".cache"

        gen = RepoMapGenerator(cache_dir=cache_dir)
        first = gen.generate(tmp_path)
        assert "first_symbol" in first
        assert any(cache_dir.rglob("*.json")), "repo-map cache should persist file metadata"

        source.write_text("def second_symbol():\n    return 2\n")
        os.utime(source, None)
        second = RepoMapGenerator(cache_dir=cache_dir).generate(tmp_path)

        assert "second_symbol" in second
        assert "first_symbol" not in second

    def test_token_budget_enforcement_is_strict(self, tmp_path):
        """Generated text should stay inside the configured approximate token budget."""
        for i in range(30):
            (tmp_path / f"module_{i:02d}.py").write_text(
                "\n".join(f"def function_with_long_name_{i}_{j}(): pass" for j in range(4))
            )

        result = RepoMapGenerator(budget_tokens=60, cache_dir=tmp_path / ".cache").generate(
            tmp_path
        )

        assert len(result) <= 60 * 4
        assert "...(truncated)" in result

    def test_multilanguage_python_and_go_output(self, tmp_path):
        """Repo map should include supported non-Python files in the same markdown output."""
        (tmp_path / "main.py").write_text("class PythonWorker:\n    pass\n")
        (tmp_path / "server.go").write_text(textwrap.dedent("""\
            package main

            import "fmt"

            type GoWorker struct {}

            func Serve() {
                fmt.Println("ok")
            }
        """))

        result = RepoMapGenerator(cache_dir=tmp_path / ".cache").generate(tmp_path)

        assert "main.py" in result
        assert "PythonWorker" in result
        assert "server.go" in result
        assert "GoWorker" in result
        assert "Serve" in result
