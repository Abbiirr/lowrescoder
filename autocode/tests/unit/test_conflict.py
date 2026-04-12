"""Tests for edit conflict detection."""

from __future__ import annotations

import os
import time
from pathlib import Path

from autocode.agent.conflict import (
    check_file_conflict,
    check_conflicts_batch,
    has_any_conflict,
)


def test_no_conflict(tmp_path: Path) -> None:
    """No conflict when mtime matches."""
    f = tmp_path / "test.py"
    f.write_text("content\n")
    mtime = os.path.getmtime(f)

    result = check_file_conflict(f, mtime)
    assert not result.has_conflict


def test_conflict_detected(tmp_path: Path) -> None:
    """Conflict detected when file modified externally."""
    f = tmp_path / "test.py"
    f.write_text("original\n")
    old_mtime = os.path.getmtime(f)

    time.sleep(0.05)
    f.write_text("modified externally\n")

    result = check_file_conflict(f, old_mtime)
    assert result.has_conflict
    assert "modified externally" in result.message


def test_missing_file(tmp_path: Path) -> None:
    """No crash on missing file."""
    f = tmp_path / "missing.py"
    result = check_file_conflict(f, 0.0)
    assert not result.has_conflict
    assert "does not exist" in result.message


def test_batch_check(tmp_path: Path) -> None:
    """Batch check multiple files."""
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("a\n")
    b.write_text("b\n")
    mtimes = {str(a): os.path.getmtime(a), str(b): os.path.getmtime(b)}

    results = check_conflicts_batch(mtimes)
    assert len(results) == 2
    assert not has_any_conflict(results)


def test_batch_with_conflict(tmp_path: Path) -> None:
    """Batch detects conflict in one file."""
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("a\n")
    b.write_text("b\n")
    mtimes = {str(a): os.path.getmtime(a), str(b): os.path.getmtime(b)}

    time.sleep(0.05)
    b.write_text("b modified\n")

    results = check_conflicts_batch(mtimes)
    assert has_any_conflict(results)
