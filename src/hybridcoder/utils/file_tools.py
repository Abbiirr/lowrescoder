"""File operation utilities for HybridCoder.

All file I/O goes through these functions to enforce path safety.
"""

from __future__ import annotations

from pathlib import Path


def _resolve_path(path: Path, project_root: Path) -> Path:
    """Resolve path relative to project_root if not absolute."""
    if not path.is_absolute():
        return (project_root / path).resolve()
    return path.resolve()


def _validate_path(path: Path, project_root: Path) -> Path:
    """Ensure path is within project root (no traversal attacks)."""
    root_resolved = project_root.resolve()
    resolved = _resolve_path(path, root_resolved)
    if resolved != root_resolved and root_resolved not in resolved.parents:
        msg = f"Path escapes project root: {path}"
        raise ValueError(msg)
    return resolved


def read_file(
    path: str | Path,
    project_root: str | Path | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
) -> str:
    """Read a file, optionally returning a line range.

    Args:
        path: File path (absolute or relative to project_root).
        project_root: Project root for path validation. If None, skips validation.
        start_line: 1-based start line (inclusive).
        end_line: 1-based end line (inclusive). None = to end of file.
    """
    file_path = Path(path)
    if project_root is not None:
        root = Path(project_root)
        file_path = _validate_path(file_path, root)
    elif not file_path.is_absolute():
        file_path = file_path.resolve()

    content = file_path.read_text(encoding="utf-8")

    if start_line is not None:
        lines = content.splitlines(keepends=True)
        start_idx = max(0, start_line - 1)
        end_idx = end_line if end_line is not None else len(lines)
        content = "".join(lines[start_idx:end_idx])

    return content


def write_file(
    path: str | Path,
    content: str,
    project_root: str | Path | None = None,
) -> Path:
    """Write content to a file.

    Args:
        path: File path (absolute or relative to project_root).
        content: Content to write.
        project_root: Project root for path validation. If None, skips validation.
    """
    file_path = Path(path)
    if project_root is not None:
        root = Path(project_root)
        file_path = _validate_path(file_path, root)
    elif not file_path.is_absolute():
        file_path = file_path.resolve()

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return file_path


def list_files(
    directory: str | Path,
    pattern: str = "*",
    project_root: str | Path | None = None,
) -> list[str]:
    """List files in a directory matching a glob pattern.

    Args:
        directory: Directory to search.
        pattern: Glob pattern (default "*").
        project_root: Project root for path validation. If None, skips validation.

    Returns:
        List of relative paths (strings) from directory.
    """
    dir_path = Path(directory)
    if project_root is not None:
        root = Path(project_root)
        dir_path = _validate_path(dir_path, root)
    elif not dir_path.is_absolute():
        dir_path = dir_path.resolve()

    if not dir_path.is_dir():
        return []

    return sorted(str(p.relative_to(dir_path)) for p in dir_path.rglob(pattern) if p.is_file())
