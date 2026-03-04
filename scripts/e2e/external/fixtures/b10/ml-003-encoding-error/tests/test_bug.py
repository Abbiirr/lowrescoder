"""Tests for encoding error bug in CSV reader."""
import sys
import os
import locale
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import read_csv, get_column, search_csv


def _write_utf8_csv(tmp_path, filename, content):
    """Write a UTF-8 encoded CSV file."""
    p = tmp_path / filename
    p.write_bytes(content.encode("utf-8"))
    return str(p)


def test_reads_ascii_csv(tmp_path):
    """Basic ASCII CSV should be readable."""
    path = _write_utf8_csv(tmp_path, "simple.csv", "name,age\nAlice,30\nBob,25\n")
    rows = read_csv(path)
    assert len(rows) == 3
    assert rows[0] == ["name", "age"]
    assert rows[1] == ["Alice", "30"]


def test_reads_utf8_names(tmp_path):
    """CSV with accented characters must be read correctly.

    This test forces the C locale to simulate a non-UTF-8 default encoding,
    which exposes the missing encoding='utf-8' parameter.
    """
    old_locale = os.environ.get("LC_ALL")
    try:
        os.environ["LC_ALL"] = "C"
        path = _write_utf8_csv(
            tmp_path, "intl.csv",
            "name,city\nJos\u00e9,S\u00e3o Paulo\nM\u00fcller,Z\u00fcrich\n"
        )
        rows = read_csv(path)
        assert len(rows) == 3
        assert "Jos\u00e9" in rows[1][0], f"Expected 'Jos\u00e9', got {rows[1][0]!r}"
        assert "S\u00e3o Paulo" in rows[1][1]
    finally:
        if old_locale is None:
            os.environ.pop("LC_ALL", None)
        else:
            os.environ["LC_ALL"] = old_locale


def test_reads_utf8_emoji(tmp_path):
    """CSV with emoji characters should work."""
    path = _write_utf8_csv(
        tmp_path, "emoji.csv",
        "item,status\ncoffee,\u2615 ready\nrocket,\U0001f680 launched\n"
    )
    rows = read_csv(path)
    assert len(rows) == 3
    assert "\u2615" in rows[1][1]


def test_get_column_utf8(tmp_path):
    """get_column should handle UTF-8 content."""
    path = _write_utf8_csv(
        tmp_path, "col.csv",
        "name,city\nRen\u00e9,Montr\u00e9al\n"
    )
    cities = get_column(path, 1)
    assert "Montr\u00e9al" in cities


def test_search_csv_utf8(tmp_path):
    """search_csv should find rows with UTF-8 content."""
    path = _write_utf8_csv(
        tmp_path, "search.csv",
        "name,city\nJos\u00e9,S\u00e3o Paulo\nAlice,London\n"
    )
    results = search_csv(path, 1, "S\u00e3o")
    assert len(results) == 1
    assert results[0][0] == "Jos\u00e9"
