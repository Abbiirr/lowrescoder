"""Tests for Layer 1 active working-set symbol previews."""

from __future__ import annotations

from unittest.mock import Mock

from autocode.core.types import Symbol
from autocode.layer1.preview import build_active_symbol_preview


def test_symbol_preview_uses_cached_parse_only(tmp_path) -> None:
    """Missing cache entries should not trigger a cold parse."""
    parser = Mock()
    parser.get_cached.return_value = None
    parser.parse.side_effect = AssertionError("cold parse is forbidden")

    result = build_active_symbol_preview(
        project_root=tmp_path,
        working_set=["src/missing.py"],
        parser=parser,
    )

    assert result == ""
    parser.get_cached.assert_called_once()
    parser.parse.assert_not_called()


def test_symbol_preview_deadline_zero_skips_lookup(tmp_path) -> None:
    """An expired preview budget should skip parser/cache access."""
    parser = Mock()

    result = build_active_symbol_preview(
        project_root=tmp_path,
        working_set=["src/hot.py"],
        parser=parser,
        deadline_ms=0,
    )

    assert result == ""
    parser.get_cached.assert_not_called()


def test_symbol_preview_respects_file_and_symbol_bounds(tmp_path) -> None:
    """Preview output should stay bounded by file and per-file symbol caps."""
    parser = Mock()
    parser.get_cached.return_value = object()
    extractor = Mock()
    extractor.extract.return_value = [
        Symbol(
            name=f"symbol_{idx}",
            kind="function",
            file="src/hot.py",
            line=idx + 1,
            end_line=idx + 1,
        )
        for idx in range(12)
    ]

    result = build_active_symbol_preview(
        project_root=tmp_path,
        working_set=["src/a.py", "src/b.py", "src/c.py"],
        parser=parser,
        extractor=extractor,
        max_files=2,
        max_symbols_per_file=3,
        max_tokens=1000,
    )

    assert "src/a.py" in result
    assert "src/b.py" in result
    assert "src/c.py" not in result
    assert "function symbol_2" in result
    assert "function symbol_3" not in result
