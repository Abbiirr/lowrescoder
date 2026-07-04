"""Tests for cross-file refactoring."""

from __future__ import annotations

from pathlib import Path

from autocode.agent.refactor import (
    apply_rename,
    find_symbol_occurrences,
    format_rename_preview,
    preview_rename,
)


def _make_project(tmp_path: Path) -> Path:
    """Create a multi-file project for refactoring tests."""
    (tmp_path / "app.py").write_text(
        "from utils import helper_func\n\n"
        "def main():\n"
        "    result = helper_func(42)\n"
        "    return result\n"
    )
    (tmp_path / "utils.py").write_text(
        "def helper_func(x):\n"
        "    return x * 2\n"
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_app.py").write_text(
        "from utils import helper_func\n\n"
        "def test_helper():\n"
        "    assert helper_func(5) == 10\n"
    )
    return tmp_path


def test_find_occurrences(tmp_path: Path) -> None:
    """Find all occurrences of a symbol across files."""
    project = _make_project(tmp_path)
    occs = find_symbol_occurrences("helper_func", project)
    assert len(occs) >= 4  # definition + 3 usages
    files = {o.file for o in occs}
    assert "app.py" in files
    assert "utils.py" in files


def test_find_respects_word_boundary(tmp_path: Path) -> None:
    """Word boundary matching prevents partial matches."""
    (tmp_path / "code.py").write_text("helper_func_extra = 1\nhelper_func = 2\n")
    occs = find_symbol_occurrences("helper_func", tmp_path)
    # Should match "helper_func" but NOT "helper_func_extra"
    assert all("helper_func" in o.context for o in occs)


def test_preview_rename(tmp_path: Path) -> None:
    """Preview shows all occurrences without modifying files."""
    project = _make_project(tmp_path)
    result = preview_rename("helper_func", "process_value", project)
    assert result.success
    assert result.occurrence_count >= 4
    assert len(result.files_modified) >= 2
    # Files should NOT be modified yet
    assert "helper_func" in (project / "utils.py").read_text()


def test_apply_rename(tmp_path: Path) -> None:
    """Apply rename changes all occurrences across files."""
    project = _make_project(tmp_path)
    result = apply_rename("helper_func", "process_value", project)
    assert result.success
    assert len(result.files_modified) >= 2

    # Verify files were actually changed
    assert "process_value" in (project / "utils.py").read_text()
    assert "process_value" in (project / "app.py").read_text()
    assert "process_value" in (project / "tests" / "test_app.py").read_text()
    assert "helper_func" not in (project / "utils.py").read_text()


def test_rename_same_name(tmp_path: Path) -> None:
    """Rename to same name returns error."""
    _make_project(tmp_path)
    result = preview_rename("helper_func", "helper_func", tmp_path)
    assert not result.success
    assert "same" in result.error


def test_format_preview(tmp_path: Path) -> None:
    """Preview formatting shows file and line info."""
    project = _make_project(tmp_path)
    result = preview_rename("helper_func", "process", project)
    output = format_rename_preview(result)
    assert "helper_func" in output
    assert "process" in output
    assert "utils.py" in output


def test_skips_venv(tmp_path: Path) -> None:
    """Skips .venv directories."""
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "module.py").write_text("target = 1\n")
    (tmp_path / "real.py").write_text("target = 2\n")

    occs = find_symbol_occurrences("target", tmp_path)
    files = {o.file for o in occs}
    assert "real.py" in files
    assert not any(".venv" in f for f in files)
