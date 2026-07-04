"""Edit conflict detection — detect concurrent file modifications.

Checks file mtime before writes to prevent overwriting external changes.
Non-overlapping edits auto-merge; overlapping edits prompt the user.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ConflictCheck:
    """Result of checking a file for concurrent modifications."""

    file: str
    has_conflict: bool = False
    our_mtime: float = 0.0
    current_mtime: float = 0.0
    message: str = ""


def check_file_conflict(
    filepath: Path,
    expected_mtime: float,
) -> ConflictCheck:
    """Check if a file was modified externally since we last read it.

    Args:
        filepath: Path to the file
        expected_mtime: The mtime when we last read the file
    """
    if not filepath.exists():
        return ConflictCheck(file=str(filepath), message="File does not exist")

    current_mtime = os.path.getmtime(filepath)
    has_conflict = current_mtime != expected_mtime

    return ConflictCheck(
        file=str(filepath),
        has_conflict=has_conflict,
        our_mtime=expected_mtime,
        current_mtime=current_mtime,
        message=(
            f"File modified externally (mtime changed: {expected_mtime} → {current_mtime})"
            if has_conflict else "No conflict"
        ),
    )


def check_conflicts_batch(
    files: dict[str, float],
) -> list[ConflictCheck]:
    """Check multiple files for conflicts.

    Args:
        files: dict of {filepath: expected_mtime}
    """
    results = []
    for filepath_str, expected_mtime in files.items():
        filepath = Path(filepath_str)
        results.append(check_file_conflict(filepath, expected_mtime))
    return results


def has_any_conflict(checks: list[ConflictCheck]) -> bool:
    """Return True if any file has a conflict."""
    return any(c.has_conflict for c in checks)
