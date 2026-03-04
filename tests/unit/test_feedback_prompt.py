"""Tests for source discovery in feedback prompt (Phase 1)."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.adapters.autocode_adapter import AutoCodeAdapter  # noqa: E402


class TestExtractTracebackPaths:
    """Tests for _extract_traceback_paths()."""

    def test_basic_traceback(self) -> None:
        output = (
            'Traceback (most recent call last):\n'
            '  File "/work/src/mymodule.py", line 42, in func\n'
            '    raise ValueError("bad")\n'
            'ValueError: bad'
        )
        paths = AutoCodeAdapter._extract_traceback_paths(output)
        assert "/work/src/mymodule.py" in paths

    def test_filters_site_packages(self) -> None:
        output = (
            '  File "/usr/lib/python3.11/site-packages/flask/app.py", '
            'line 10, in run\n'
            '  File "/work/app.py", line 5, in handler\n'
        )
        paths = AutoCodeAdapter._extract_traceback_paths(output)
        assert "/work/app.py" in paths
        assert not any("site-packages" in p for p in paths)

    def test_filters_stdlib(self) -> None:
        output = (
            '  File "/usr/lib/python3.11/unittest/runner.py", '
            'line 100, in run\n'
        )
        paths = AutoCodeAdapter._extract_traceback_paths(output)
        assert len(paths) == 0

    def test_empty_output(self) -> None:
        assert AutoCodeAdapter._extract_traceback_paths("") == []


class TestExtractImportsFromPatch:
    """Tests for _extract_imports_from_patch()."""

    def test_from_import(self) -> None:
        patch = (
            "+from _pytest.unittest import TestCaseFunction\n"
            "+from _pytest.python import Module\n"
        )
        modules = AutoCodeAdapter._extract_imports_from_patch(patch)
        assert "_pytest.unittest" in modules
        assert "_pytest.python" in modules

    def test_plain_import(self) -> None:
        patch = "+import django.db.models\n"
        modules = AutoCodeAdapter._extract_imports_from_patch(patch)
        assert "django.db.models" in modules

    def test_ignores_non_added_lines(self) -> None:
        patch = (
            "from _pytest.unittest import TestCaseFunction\n"  # no +
            "-from old_module import Foo\n"
        )
        modules = AutoCodeAdapter._extract_imports_from_patch(patch)
        assert len(modules) == 0

    def test_empty_patch(self) -> None:
        assert AutoCodeAdapter._extract_imports_from_patch("") == []


class TestTestNameToSourceHints:
    """Tests for _test_name_to_source_hints()."""

    def test_strips_test_prefix(self) -> None:
        failing = ["FAILED testing/test_unittest.py::TestCase"]
        hints = AutoCodeAdapter._test_name_to_source_hints(failing)
        assert "unittest.py" in hints

    def test_strips_test_suffix(self) -> None:
        failing = ["FAILED tests/aggregates_test.py::TestAgg"]
        hints = AutoCodeAdapter._test_name_to_source_hints(failing)
        assert "aggregates.py" in hints

    def test_no_test_pattern(self) -> None:
        failing = ["FAILED tests/conftest.py::setup"]
        hints = AutoCodeAdapter._test_name_to_source_hints(failing)
        assert len(hints) == 0

    def test_deduplicates(self) -> None:
        failing = [
            "FAILED testing/test_foo.py::test_a",
            "FAILED testing/test_foo.py::test_b",
        ]
        hints = AutoCodeAdapter._test_name_to_source_hints(failing)
        assert hints.count("foo.py") == 1


class TestExtractDiffFilePaths:
    """Tests for _extract_diff_file_paths()."""

    def test_diff_git_header(self) -> None:
        patch = (
            "diff --git a/testing/test_unittest.py "
            "b/testing/test_unittest.py\n"
            "--- a/testing/test_unittest.py\n"
            "+++ b/testing/test_unittest.py\n"
        )
        paths = AutoCodeAdapter._extract_diff_file_paths(patch)
        assert "testing/test_unittest.py" in paths
        # Should deduplicate
        assert paths.count("testing/test_unittest.py") == 1

    def test_multiple_files(self) -> None:
        patch = (
            "diff --git a/tests/test_a.py b/tests/test_a.py\n"
            "+++ b/tests/test_a.py\n"
            "diff --git a/tests/test_b.py b/tests/test_b.py\n"
            "+++ b/tests/test_b.py\n"
        )
        paths = AutoCodeAdapter._extract_diff_file_paths(patch)
        assert len(paths) == 2

    def test_empty_patch(self) -> None:
        assert AutoCodeAdapter._extract_diff_file_paths("") == []


class TestTestPathToSourceCandidates:
    """Tests for _test_path_to_source_candidates()."""

    def test_pytest_style_testing_dir(self) -> None:
        """testing/test_unittest.py -> src/_pytest/unittest.py."""
        candidates = AutoCodeAdapter._test_path_to_source_candidates(
            "testing/test_unittest.py",
        )
        assert "src/_pytest/unittest.py" in candidates
        assert "_pytest/unittest.py" in candidates
        assert "src/unittest.py" in candidates

    def test_tests_dir(self) -> None:
        """tests/test_foo.py -> src/_pytest/foo.py, src/foo.py."""
        candidates = AutoCodeAdapter._test_path_to_source_candidates(
            "tests/test_foo.py",
        )
        assert "src/_pytest/foo.py" in candidates
        assert "src/foo.py" in candidates
        assert "foo.py" in candidates

    def test_suffix_style(self) -> None:
        """tests/aggregates_test.py -> aggregates.py candidates."""
        candidates = AutoCodeAdapter._test_path_to_source_candidates(
            "tests/aggregates_test.py",
        )
        assert any("aggregates.py" in c for c in candidates)

    def test_non_test_file_returns_empty(self) -> None:
        candidates = AutoCodeAdapter._test_path_to_source_candidates(
            "src/conftest.py",
        )
        assert candidates == []


class TestDiscoverSourceCandidates:
    """Tests for _discover_source_candidates()."""

    def test_combines_signals(self) -> None:
        adapter = AutoCodeAdapter.__new__(AutoCodeAdapter)
        grading_output = (
            '  File "/work/src/core.py", line 10, in handle\n'
        )
        test_patch = "+from mypackage.utils import helper\n"
        failing_tests = ["FAILED tests/test_utils.py::test_helper"]

        candidates = adapter._discover_source_candidates(
            grading_output, test_patch, failing_tests,
        )
        # Should have traceback path, import module, and test name hint
        assert any("core.py" in c for c in candidates)
        assert any("mypackage/utils.py" in c for c in candidates)
        assert any("utils.py" in c for c in candidates)

    def test_filters_test_files_from_tracebacks(self) -> None:
        adapter = AutoCodeAdapter.__new__(AutoCodeAdapter)
        grading_output = (
            '  File "/work/testing/test_foo.py", line 5, in test_bar\n'
            '  File "/work/src/foo.py", line 10, in bar\n'
        )
        candidates = adapter._discover_source_candidates(
            grading_output, "", [],
        )
        paths = [c for c in candidates if not c.startswith("(")]
        assert any("src/foo.py" in p for p in paths)
        assert not any("test_foo.py" in p for p in paths)

    def test_empty_inputs(self) -> None:
        adapter = AutoCodeAdapter.__new__(AutoCodeAdapter)
        candidates = adapter._discover_source_candidates("", "", [])
        assert candidates == []

    def test_real_pytest_10081_test_patch(self) -> None:
        """Regression test using the REAL pytest-10081 test_patch.

        The test_patch modifies testing/test_unittest.py but does NOT
        contain 'from _pytest.unittest import'. Signal 4 (diff header
        path mapping) should produce src/_pytest/unittest.py as a
        candidate.
        """
        adapter = AutoCodeAdapter.__new__(AutoCodeAdapter)
        # Minimal reproduction of the real diff headers
        real_test_patch = (
            "diff --git a/testing/test_unittest.py "
            "b/testing/test_unittest.py\n"
            "--- a/testing/test_unittest.py\n"
            "+++ b/testing/test_unittest.py\n"
            "@@ -1241,12 +1241,15 @@\n"
            "+def test_pdb_teardown_skipped_for_classes(\n"
            "+    pytester: Pytester, monkeypatch: MonkeyPatch,\n"
            "+) -> None:\n"
            '+        import unittest\n'
            '+        import pytest\n'
        )
        failing_tests = [
            "FAILED testing/test_unittest.py::"
            "test_pdb_teardown_skipped_for_classes",
        ]

        candidates = adapter._discover_source_candidates(
            "", real_test_patch, failing_tests,
        )
        joined = " ".join(candidates)
        # Signal 4 should produce _pytest/unittest.py
        assert "src/_pytest/unittest.py" in joined, (
            f"Expected src/_pytest/unittest.py in candidates: {candidates}"
        )
        # Signal 3 should produce unittest.py hint
        assert "unittest.py" in joined
