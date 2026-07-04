"""@file reference detection, resolution, and fuzzy completion."""

from __future__ import annotations

import re
from pathlib import Path

# Matches @path and @path:start-end patterns
_AT_REF_PATTERN = re.compile(r"@([\w./\\-]+(?::(\d+)(?:-(\d+))?)?)(?=\s|$)")


def detect_at_references(text: str) -> list[str]:
    """Find all @path references in text.

    Returns raw reference strings (without the @).
    """
    return [m.group(1) for m in _AT_REF_PATTERN.finditer(text)]


def resolve_reference(ref: str, project_root: Path) -> str:
    """Resolve a single @reference to file content.

    Supports:
      - @path → full file content
      - @path:start-end → line range
    """
    parts = ref.split(":")
    path_str = parts[0]
    file_path = project_root / path_str

    if not file_path.is_file():
        return f"[File not found: {path_str}]"

    try:
        content = file_path.read_text(encoding="utf-8")
    except (PermissionError, OSError) as e:
        return f"[Error reading {path_str}: {e}]"

    if len(parts) == 1:
        return content

    # Parse line range
    range_str = parts[1]
    if "-" in range_str:
        start_str, end_str = range_str.split("-", 1)
        start = int(start_str) if start_str else 1
        end = int(end_str) if end_str else None
    else:
        start = int(range_str)
        end = start

    lines = content.splitlines(keepends=True)
    start_idx = max(0, start - 1)
    end_idx = end if end is not None else len(lines)
    return "".join(lines[start_idx:end_idx])


def expand_references(text: str, project_root: Path) -> str:
    """Replace all @references in text with file contents."""
    refs = detect_at_references(text)
    if not refs:
        return text

    result = text
    for ref in refs:
        content = resolve_reference(ref, project_root)
        # Add file header for clarity
        path_part = ref.split(":")[0]
        replacement = f"\n--- {path_part} ---\n{content}\n---\n"
        result = result.replace(f"@{ref}", replacement, 1)
    return result


def fuzzy_complete(partial: str, project_root: Path, max_results: int = 10) -> list[str]:
    """Match a partial path against project files.

    Returns relative paths matching the partial string.
    """
    partial_lower = partial.lower()
    matches: list[tuple[int, str]] = []

    # Common directories to skip
    skip_dirs = {".git", "__pycache__", "node_modules", ".venv", ".mypy_cache", ".pytest_cache"}

    for file_path in project_root.rglob("*"):
        if file_path.is_dir():
            continue
        # Skip files in excluded directories
        if any(part in skip_dirs for part in file_path.parts):
            continue

        rel = str(file_path.relative_to(project_root)).replace("\\", "/")
        rel_lower = rel.lower()

        if partial_lower in rel_lower:
            # Score by position — earlier match is better
            idx = rel_lower.index(partial_lower)
            matches.append((idx, rel))

    matches.sort(key=lambda x: (x[0], x[1]))
    return [m[1] for m in matches[:max_results]]
