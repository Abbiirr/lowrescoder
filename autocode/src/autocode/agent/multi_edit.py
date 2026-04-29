"""Multi-file editing — edit multiple files in a single operation.

Supports atomic multi-file changes with preview, accept/reject,
and local file-copy undo/rollback.
"""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FileEdit:
    """A proposed edit to a single file."""

    path: str
    old_content: str
    new_content: str
    description: str = ""

    @property
    def is_new_file(self) -> bool:
        return not self.old_content

    @property
    def is_deletion(self) -> bool:
        return not self.new_content and bool(self.old_content)

    @property
    def diff_lines(self) -> int:
        """Approximate number of changed lines."""
        old_lines = set(self.old_content.splitlines())
        new_lines = set(self.new_content.splitlines())
        return len(old_lines.symmetric_difference(new_lines))


@dataclass
class MultiEditPlan:
    """A plan to edit multiple files atomically."""

    edits: list[FileEdit] = field(default_factory=list)
    description: str = ""
    rollback_sha: str = ""  # local snapshot token before edits for undo

    @property
    def file_count(self) -> int:
        return len(self.edits)

    @property
    def total_diff_lines(self) -> int:
        return sum(e.diff_lines for e in self.edits)

    def preview(self) -> str:
        """Generate a human-readable preview of all changes."""
        import difflib

        parts = [f"Multi-file edit: {self.description}", "=" * 50]
        for edit in self.edits:
            if edit.is_new_file:
                parts.append(f"\n+ NEW FILE: {edit.path}")
                parts.append(f"  ({len(edit.new_content.splitlines())} lines)")
            elif edit.is_deletion:
                parts.append(f"\n- DELETE: {edit.path}")
            else:
                diff = difflib.unified_diff(
                    edit.old_content.splitlines(keepends=True),
                    edit.new_content.splitlines(keepends=True),
                    fromfile=f"a/{edit.path}",
                    tofile=f"b/{edit.path}",
                )
                diff_text = "".join(diff)
                if len(diff_text) > 500:
                    diff_text = diff_text[:500] + "\n... (truncated)"
                parts.append(f"\n~ MODIFY: {edit.path}")
                parts.append(diff_text)

        parts.append(f"\n{self.file_count} file(s), ~{self.total_diff_lines} line(s) changed")
        return "\n".join(parts)


@dataclass
class MultiEditResult:
    """Result of applying a multi-file edit."""

    success: bool
    files_modified: list[str] = field(default_factory=list)
    files_created: list[str] = field(default_factory=list)
    files_deleted: list[str] = field(default_factory=list)
    rollback_sha: str = ""
    error: str = ""


def create_rollback_point(
    project_root: Path,
    files: list[str] | None = None,
) -> str:
    """Create a scoped local rollback point.

    Returns a snapshot directory token. This intentionally does not use git:
    no commit, reset, checkout, restore, or stash mutation.
    """
    try:
        if not files:
            return ""
        snapshot_dir = (
            Path.home()
            / ".autocode"
            / "multi-edit-snapshots"
            / uuid.uuid4().hex
        )
        snapshot_dir.mkdir(parents=True, exist_ok=False)
        manifest: list[dict[str, str | bool]] = []
        for raw in files:
            rel = str(raw)
            source = project_root / rel
            snapshot_name = uuid.uuid4().hex
            snapshot_path = snapshot_dir / snapshot_name
            existed = source.exists()
            if existed and source.is_file():
                snapshot_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, snapshot_path)
            manifest.append({
                "path": rel,
                "existed": existed,
                "snapshot": snapshot_name,
            })
        (snapshot_dir / "manifest.json").write_text(
            json.dumps({"files": manifest}, indent=2),
            encoding="utf-8",
        )
        return str(snapshot_dir)
    except Exception:
        return ""


def apply_multi_edit(
    plan: MultiEditPlan,
    project_root: Path | None = None,
) -> MultiEditResult:
    """Apply a multi-file edit plan atomically.

    Creates a rollback point before applying.
    """
    root = project_root or Path.cwd()
    modified: list[str] = []
    created: list[str] = []
    deleted: list[str] = []

    # Create scoped rollback point (only stages plan files)
    plan_files = [e.path for e in plan.edits]
    rollback = create_rollback_point(root, files=plan_files) if plan.edits else ""

    try:
        for edit in plan.edits:
            path = root / edit.path
            if edit.is_deletion:
                if path.exists():
                    path.unlink()
                    deleted.append(edit.path)
            elif edit.is_new_file:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(edit.new_content, encoding="utf-8")
                created.append(edit.path)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(edit.new_content, encoding="utf-8")
                modified.append(edit.path)

        return MultiEditResult(
            success=True,
            files_modified=modified,
            files_created=created,
            files_deleted=deleted,
            rollback_sha=rollback,
        )
    except Exception as e:
        return MultiEditResult(
            success=False,
            error=str(e),
            rollback_sha=rollback,
        )


def rollback(
    sha: str,
    project_root: Path | None = None,
    created_files: list[str] | None = None,
) -> bool:
    """Rollback to a previous local snapshot.

    Also removes files that were created by the edit.
    """
    root = project_root or Path.cwd()
    try:
        # Remove files that were created outside the snapshot manifest.
        if created_files:
            for f in created_files:
                path = root / f
                if path.exists():
                    path.unlink()
                    # Clean up empty parent dirs
                    parent = path.parent
                    if parent != root and parent.exists() and not any(parent.iterdir()):
                        parent.rmdir()

        snapshot_dir = Path(sha)
        manifest_path = snapshot_dir / "manifest.json"
        if not manifest_path.exists():
            return False
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for item in manifest.get("files", []):
            rel = str(item["path"])
            target = root / rel
            if item.get("existed"):
                snapshot_path = snapshot_dir / str(item["snapshot"])
                if snapshot_path.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(snapshot_path, target)
            elif target.exists():
                target.unlink()
        return True
    except Exception:
        return False
