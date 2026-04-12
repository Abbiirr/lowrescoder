"""Tests for the repo map generator (Sprint 3F)."""

from __future__ import annotations

import textwrap

from autocode.layer2.repomap import RepoMapGenerator


class TestRepoMapGenerator:
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
