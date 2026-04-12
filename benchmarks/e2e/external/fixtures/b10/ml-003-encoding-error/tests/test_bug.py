"""Tests for encoding error bug in CSV reader.

These tests write files as raw UTF-8 bytes, then read them using the
app functions. If the app does not specify encoding='utf-8', it will
fail when the system locale is not UTF-8 (simulated via PYTHONIOENCODING
and/or by writing files that contain non-ASCII bytes).
"""
import sys
import os
import subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import read_csv, read_csv_with_header, write_csv


def _write_raw_utf8(filepath, content_str):
    """Write content as raw UTF-8 bytes (bypasses system encoding)."""
    with open(filepath, "wb") as f:
        f.write(content_str.encode("utf-8"))


def test_reads_ascii_csv(tmp_path):
    """Basic ASCII CSV should always work."""
    p = tmp_path / "simple.csv"
    _write_raw_utf8(p, "name,age\nAlice,30\nBob,25\n")
    rows = read_csv(str(p))
    assert len(rows) == 3
    assert rows[0] == ["name", "age"]
    assert rows[1] == ["Alice", "30"]


def test_reads_utf8_in_subprocess(tmp_path):
    """Read a UTF-8 CSV in a subprocess with C locale to expose the bug.

    When LANG=C and PYTHONIOENCODING is not set to utf-8, Python's
    default encoding is ASCII, so open() without encoding='utf-8'
    will raise UnicodeDecodeError on non-ASCII content.
    """
    csv_path = tmp_path / "intl.csv"
    _write_raw_utf8(csv_path, "name,city\nJos\u00e9,S\u00e3o Paulo\n")

    # Run a subprocess with C locale to force ASCII default encoding
    script = (
        f"import sys; sys.path.insert(0, {str(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))!r}); "
        f"from app import read_csv; rows = read_csv({str(csv_path)!r}); "
        f"assert len(rows) == 2, f'Expected 2 rows, got {{len(rows)}}'; "
        f"assert 'Jos\\u00e9' in rows[1][0], f'Expected Jos\\u00e9, got {{rows[1][0]!r}}'; "
        f"print('OK')"
    )

    env = os.environ.copy()
    env["LANG"] = "C"
    env["LC_ALL"] = "C"
    env.pop("PYTHONIOENCODING", None)
    # Force Python to use ASCII as default encoding
    env["PYTHONCOERCECLOCALE"] = "0"

    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, (
        f"UTF-8 CSV reading failed with C locale.\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}\n"
        f"This means open() is not specifying encoding='utf-8'"
    )


def test_roundtrip_utf8(tmp_path):
    """Write then read should preserve UTF-8 content in C locale."""
    csv_path = tmp_path / "roundtrip.csv"

    script = (
        f"import sys; sys.path.insert(0, {str(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))!r}); "
        f"from app import write_csv, read_csv; "
        f"write_csv({str(csv_path)!r}, [['name', 'city'], ['Ren\\u00e9', 'Montr\\u00e9al']]); "
        f"rows = read_csv({str(csv_path)!r}); "
        f"assert rows[1][0] == 'Ren\\u00e9', f'Expected Ren\\u00e9, got {{rows[1][0]!r}}'; "
        f"print('OK')"
    )

    env = os.environ.copy()
    env["LANG"] = "C"
    env["LC_ALL"] = "C"
    env.pop("PYTHONIOENCODING", None)
    env["PYTHONCOERCECLOCALE"] = "0"

    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, (
        f"UTF-8 CSV roundtrip failed with C locale.\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}\n"
        f"This means open() is not specifying encoding='utf-8'"
    )


def test_read_csv_with_header(tmp_path):
    """read_csv_with_header should separate header from data rows."""
    p = tmp_path / "headed.csv"
    _write_raw_utf8(p, "name,score\nAlice,95\nBob,87\n")
    header, rows = read_csv_with_header(str(p))
    assert header == ["name", "score"]
    assert len(rows) == 2


def test_write_csv_creates_file(tmp_path):
    """write_csv should create a readable CSV file."""
    p = tmp_path / "output.csv"
    write_csv(str(p), [["a", "b"], ["1", "2"]])
    rows = read_csv(str(p))
    assert rows[0] == ["a", "b"]
    assert rows[1] == ["1", "2"]
