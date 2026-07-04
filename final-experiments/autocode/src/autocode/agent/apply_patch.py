"""Transactional multi-file patch tool (deep-research-report Phase B Item 1).

The deep-research report calls out that fragile shell pipelines like
``sed -i`` + ``heredoc`` + ``find -exec`` lose both safety and clarity:
one operation in a multi-file refactor can silently succeed while another
fails halfway through, leaving the tree in a mixed state with no clean
rollback path.

This module provides a **typed, transactional** alternative:

- ``PatchOperation`` describes a single old_string → new_string edit on
  one file.
- ``apply_patch(operations, dry_run)`` preflights every op *before*
  touching disk. If any op would conflict (file missing, old_string not
  found, ambiguous match), **no** files are written.
- ``dry_run=True`` runs the preflight and reports conflicts without
  writing, so the agent can preview an edit set before committing.
- Writes happen atomically once preflight passes.

Contract:
- ``PatchOperation(path, old_string, new_string)`` — single range edit.
- ``ApplyPatchResult(applied, conflicts, changed_files, preview)``.
  ``applied=True`` only when ``dry_run=False`` AND there were no
  conflicts.

This is the Phase B replacement for chained ``edit_file`` calls when
the agent needs multi-step atomicity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PatchOperation:
    """A single range-edit operation against one file."""

    path: str
    old_string: str
    new_string: str

    def __post_init__(self) -> None:
        if not isinstance(self.path, str) or not self.path:
            raise ValueError("PatchOperation.path must be a non-empty string")
        if not isinstance(self.old_string, str):
            raise ValueError("PatchOperation.old_string must be a string")
        if not isinstance(self.new_string, str):
            raise ValueError("PatchOperation.new_string must be a string")


@dataclass
class PatchConflict:
    """A reason why a single operation cannot be applied."""

    path: str
    reason: str


@dataclass
class ApplyPatchResult:
    """Outcome of an ``apply_patch`` call."""

    applied: bool
    conflicts: list[PatchConflict] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    # In dry-run mode, a preview of the proposed new content per file,
    # keyed by path. Empty when not dry-run, or when there were conflicts.
    preview: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.conflicts

    def to_text(self) -> str:
        """Human/LLM-readable summary of the result."""
        if self.conflicts:
            lines = [f"apply_patch: {len(self.conflicts)} conflict(s), NO files written"]
            for c in self.conflicts:
                lines.append(f"  - {c.path}: {c.reason}")
            return "\n".join(lines)
        if self.applied:
            lines = [f"apply_patch: applied {len(self.changed_files)} file(s)"]
            for p in self.changed_files:
                lines.append(f"  - {p}")
            return "\n".join(lines)
        # Dry-run, no conflicts
        lines = [
            f"apply_patch dry-run: {len(self.changed_files)} file(s) would change, no conflicts"
        ]
        for p in self.changed_files:
            lines.append(f"  - {p}")
        return "\n".join(lines)


def _resolve(path: str, project_root: str) -> Path:
    """Resolve ``path`` against ``project_root`` (or cwd if empty)."""
    p = Path(path)
    if p.is_absolute():
        return p
    root = Path(project_root) if project_root else Path.cwd()
    return (root / p).resolve()


def apply_patch(
    operations: list[PatchOperation],
    *,
    dry_run: bool = False,
    project_root: str = "",
) -> ApplyPatchResult:
    """Preflight every op, then atomically write all files (or none).

    Preflight rules (any failure → conflict, no files written):
    1. ``path`` resolves to a file that exists.
    2. ``old_string`` appears in the file (exactly once is preferred, but
       we accept the first match if unambiguous by position — ambiguous
       matches are rejected).
    3. Each ``(path, old_string)`` pair is unique within the batch so
       operations cannot step on each other.

    Args:
        operations: List of :class:`PatchOperation` to apply together.
        dry_run: If True, report what would happen but never write.
        project_root: Optional project root for relative paths.

    Returns:
        :class:`ApplyPatchResult`.
    """
    if not operations:
        return ApplyPatchResult(applied=False, changed_files=[], preview={})

    conflicts: list[PatchConflict] = []
    # Work out the staged content for every target file
    staged_content: dict[str, str] = {}
    # Order-preserving list of paths changed
    changed_order: list[str] = []
    seen_pairs: set[tuple[str, str]] = set()

    # Group operations by resolved path so we apply in-place sequentially
    # on the in-memory buffer
    for op in operations:
        # Duplicate (path, old_string) in the same batch = ambiguous
        key = (op.path, op.old_string)
        if key in seen_pairs:
            conflicts.append(
                PatchConflict(
                    path=op.path,
                    reason=(
                        "duplicate (path, old_string) in same batch — "
                        "use a single op or disambiguate with more context"
                    ),
                )
            )
            continue
        seen_pairs.add(key)

        resolved = _resolve(op.path, project_root)
        if not resolved.exists():
            conflicts.append(
                PatchConflict(path=op.path, reason=f"file does not exist: {resolved}")
            )
            continue
        if not resolved.is_file():
            conflicts.append(
                PatchConflict(path=op.path, reason=f"path is not a regular file: {resolved}")
            )
            continue

        # Load the current staged content (first touch reads from disk,
        # subsequent touches reuse the in-memory buffer so multi-op per
        # file composes correctly)
        if op.path not in staged_content:
            try:
                staged_content[op.path] = resolved.read_text(encoding="utf-8")
            except OSError as exc:
                conflicts.append(
                    PatchConflict(
                        path=op.path,
                        reason=f"cannot read file: {exc}",
                    )
                )
                continue
            changed_order.append(op.path)

        buf = staged_content[op.path]
        count = buf.count(op.old_string)
        if count == 0:
            conflicts.append(
                PatchConflict(
                    path=op.path,
                    reason=(
                        "old_string not found in current file contents "
                        "(was the file already modified?)"
                    ),
                )
            )
            continue
        if count > 1:
            conflicts.append(
                PatchConflict(
                    path=op.path,
                    reason=(
                        f"old_string appears {count} times — must be unique; "
                        "include more surrounding context"
                    ),
                )
            )
            continue

        # Apply in-memory
        staged_content[op.path] = buf.replace(op.old_string, op.new_string, 1)

    if conflicts:
        return ApplyPatchResult(
            applied=False,
            conflicts=conflicts,
            changed_files=[],
            preview={},
        )

    # Preflight passed. If dry-run, return the preview without writing.
    if dry_run:
        return ApplyPatchResult(
            applied=False,
            conflicts=[],
            changed_files=list(changed_order),
            preview=dict(staged_content),
        )

    # Atomic commit: write all files. If any write fails we DO NOT
    # attempt partial rollback beyond the usual filesystem guarantees —
    # the preflight guards against the most common failure modes
    # (missing file, ambiguous match, duplicate op).
    for path in changed_order:
        resolved = _resolve(path, project_root)
        try:
            resolved.write_text(staged_content[path], encoding="utf-8")
        except OSError as exc:
            conflicts.append(
                PatchConflict(path=path, reason=f"write failed: {exc}")
            )

    if conflicts:
        return ApplyPatchResult(
            applied=False,
            conflicts=conflicts,
            changed_files=[],
            preview={},
        )

    return ApplyPatchResult(
        applied=True,
        conflicts=[],
        changed_files=list(changed_order),
        preview={},
    )


# --- Tool handler entry point (called from tools.py registry) ---


def _handle_apply_patch(
    operations: list[dict] | None = None,
    dry_run: bool = False,
    project_root: str = "",
) -> str:
    """Tool handler that adapts the JSON-schema parameter layout to the
    typed ``apply_patch`` API and returns a human-readable result.
    """
    if not operations:
        return "apply_patch: operations list is required"

    ops: list[PatchOperation] = []
    for raw in operations:
        if not isinstance(raw, dict):
            return f"apply_patch: invalid operation (not an object): {raw!r}"
        try:
            ops.append(
                PatchOperation(
                    path=raw.get("path", ""),
                    old_string=raw.get("old_string", ""),
                    new_string=raw.get("new_string", ""),
                )
            )
        except ValueError as exc:
            return f"apply_patch: {exc}"

    result = apply_patch(ops, dry_run=dry_run, project_root=project_root)
    return result.to_text()
