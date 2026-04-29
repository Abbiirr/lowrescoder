"""Local file-copy snapshot mechanism for per-tool-call checkpoints.

Snapshots are stored under ~/.autocode/snapshots/<session_id>/<tool_call_id>/
as plain file copies. No git stash, no git checkout, no tree-mutating git ops.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def snapshot_files(
    project_dir: Path,
    snapshot_dir: Path,
    files: list[str],
) -> list[str]:
    """Copy files from project_dir to snapshot_dir. Returns list of copied files.

    Silently skips files that don't exist on disk.
    """
    copied: list[str] = []
    for rel_path in files:
        src = project_dir / rel_path
        if not src.exists():
            logger.debug("snapshot: skipping missing file %s", rel_path)
            continue
        dst = snapshot_dir / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
        copied.append(rel_path)
    logger.info("snapshot: copied %d/%d files to %s", len(copied), len(files), snapshot_dir)
    return copied


def restore_snapshot(
    snapshot_dir: Path,
    project_dir: Path,
) -> list[str]:
    """Restore all files from snapshot_dir back to project_dir. Returns list of restored files."""
    if not snapshot_dir.exists():
        logger.warning("restore: snapshot dir does not exist: %s", snapshot_dir)
        return []
    restored: list[str] = []
    for src_file in sorted(snapshot_dir.rglob("*")):
        if src_file.is_dir():
            continue
        rel = src_file.relative_to(snapshot_dir)
        dst = project_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src_file), str(dst))
        restored.append(str(rel))
    logger.info("restore: restored %d files from %s", len(restored), snapshot_dir)
    return restored


def enforce_snapshot_retention(
    base_dir: Path,
    limit: int = 50,
) -> int:
    """Delete oldest snapshot directories beyond limit. Returns count removed.

    Assumes base_dir contains subdirectories named by tool_call_id.
    Directories are sorted by modification time (oldest first).
    """
    if not base_dir.exists():
        return 0
    dirs = sorted(
        [d for d in base_dir.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
    )
    if len(dirs) <= limit:
        return 0
    to_remove = dirs[: len(dirs) - limit]
    removed = 0
    for d in to_remove:
        shutil.rmtree(str(d))
        removed += 1
    logger.info("snapshot retention: removed %d dirs (limit=%d)", removed, limit)
    return removed
