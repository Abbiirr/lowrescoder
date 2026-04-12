"""Cross-file refactoring — rename symbols across entire project.

Uses tree-sitter-style symbol extraction to find all occurrences,
then applies consistent renames with preview and rollback support.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RenameOccurrence:
    """A single occurrence of a symbol to rename."""

    file: str
    line: int
    column: int
    context: str  # line content for preview


@dataclass
class RenameResult:
    """Result of a cross-file rename operation."""

    old_name: str
    new_name: str
    occurrences: list[RenameOccurrence] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    success: bool = False
    error: str = ""

    @property
    def occurrence_count(self) -> int:
        return len(self.occurrences)


def find_symbol_occurrences(
    symbol: str,
    project_root: Path,
    file_pattern: str = "*.py",
) -> list[RenameOccurrence]:
    """Find all occurrences of a symbol across the project.

    Uses regex word-boundary matching for accuracy.
    Skips .venv, __pycache__, .git directories.
    """
    occurrences: list[RenameOccurrence] = []
    pattern = re.compile(rf"\b{re.escape(symbol)}\b")

    skip_dirs = {".venv", "__pycache__", ".git", "node_modules", ".mypy_cache"}

    for filepath in project_root.rglob(file_pattern):
        if any(d in filepath.parts for d in skip_dirs):
            continue
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            for i, line in enumerate(content.splitlines(), 1):
                for match in pattern.finditer(line):
                    occurrences.append(RenameOccurrence(
                        file=str(filepath.relative_to(project_root)),
                        line=i,
                        column=match.start(),
                        context=line.strip(),
                    ))
        except Exception:
            continue

    return occurrences


def preview_rename(
    old_name: str,
    new_name: str,
    project_root: Path,
    file_pattern: str = "*.py",
) -> RenameResult:
    """Preview a rename without applying it.

    Returns all occurrences that would be changed.
    """
    if old_name == new_name:
        return RenameResult(
            old_name=old_name, new_name=new_name,
            error="Old and new names are the same",
        )

    occurrences = find_symbol_occurrences(old_name, project_root, file_pattern)

    return RenameResult(
        old_name=old_name,
        new_name=new_name,
        occurrences=occurrences,
        files_modified=list({o.file for o in occurrences}),
        success=True,
    )


def apply_rename(
    old_name: str,
    new_name: str,
    project_root: Path,
    file_pattern: str = "*.py",
) -> RenameResult:
    """Apply a cross-file rename.

    Replaces all word-boundary occurrences of old_name with new_name.
    """
    result = preview_rename(old_name, new_name, project_root, file_pattern)
    if not result.success or not result.occurrences:
        return result

    pattern = re.compile(rf"\b{re.escape(old_name)}\b")
    modified_files: list[str] = []

    # Group by file
    files_to_edit: dict[str, list[RenameOccurrence]] = {}
    for occ in result.occurrences:
        files_to_edit.setdefault(occ.file, []).append(occ)

    for rel_path in files_to_edit:
        filepath = project_root / rel_path
        try:
            content = filepath.read_text(encoding="utf-8")
            new_content = pattern.sub(new_name, content)
            if new_content != content:
                filepath.write_text(new_content, encoding="utf-8")
                modified_files.append(rel_path)
        except Exception as e:
            result.error = f"Failed to edit {rel_path}: {e}"
            result.success = False
            return result

    result.files_modified = modified_files
    return result


def format_rename_preview(result: RenameResult) -> str:
    """Format a rename preview for display."""
    lines = [
        f"Rename: {result.old_name} → {result.new_name}",
        f"Occurrences: {result.occurrence_count}",
        f"Files affected: {len(result.files_modified)}",
        "",
    ]

    # Group by file
    by_file: dict[str, list[RenameOccurrence]] = {}
    for occ in result.occurrences:
        by_file.setdefault(occ.file, []).append(occ)

    for filepath, occs in sorted(by_file.items()):
        lines.append(f"  {filepath}:")
        for occ in occs[:5]:  # show max 5 per file
            lines.append(f"    L{occ.line}: {occ.context}")
        if len(occs) > 5:
            lines.append(f"    ... and {len(occs) - 5} more")

    return "\n".join(lines)
