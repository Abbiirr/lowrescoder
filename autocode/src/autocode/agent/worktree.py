"""Worktree isolation for subagents and risky tasks.

Based on Claude Code's worktree isolation pattern: create a
temporary git worktree for risky operations, merge back on success.

Uses git worktrees for lightweight isolation without full clones.
"""

from __future__ import annotations

import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass
class WorktreeInfo:
    """Information about an active worktree."""

    path: Path
    branch: str
    parent_repo: Path
    worktree_id: str


def create_worktree(
    repo_root: Path,
    prefix: str = "autocode-wt",
) -> WorktreeInfo:
    """Create an isolated git worktree for a subagent.

    Creates a new branch and worktree in a temp location.
    The subagent works in the worktree; changes are merged
    back on success or discarded on failure.
    """
    wt_id = f"{prefix}-{uuid.uuid4().hex[:8]}"
    branch = f"autocode/{wt_id}"
    wt_path = repo_root.parent / ".autocode-worktrees" / wt_id

    # Create the worktree directory
    wt_path.parent.mkdir(parents=True, exist_ok=True)

    # Create worktree with new branch
    result = subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(wt_path)],
        cwd=str(repo_root),
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to create worktree: {result.stderr}")

    return WorktreeInfo(
        path=wt_path,
        branch=branch,
        parent_repo=repo_root,
        worktree_id=wt_id,
    )


def merge_worktree(info: WorktreeInfo) -> bool:
    """Merge worktree changes back into the parent branch.

    Returns True if merge succeeded.
    """
    try:
        # Check if worktree has changes
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(info.path),
            capture_output=True, text=True, timeout=10,
        )
        if status.stdout.strip():
            # Commit pending changes
            subprocess.run(
                ["git", "add", "-A"],
                cwd=str(info.path),
                capture_output=True, timeout=10,
            )
            subprocess.run(
                ["git", "commit", "-m", f"autocode: worktree {info.worktree_id}"],
                cwd=str(info.path),
                capture_output=True, timeout=10,
            )

        # Merge into parent
        result = subprocess.run(
            ["git", "merge", "--no-ff", info.branch,
             "-m", f"Merge autocode worktree {info.worktree_id}"],
            cwd=str(info.parent_repo),
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False


def cleanup_worktree(info: WorktreeInfo) -> None:
    """Remove a worktree and its branch (discard changes)."""
    try:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(info.path)],
            cwd=str(info.parent_repo),
            capture_output=True, timeout=10,
        )
        subprocess.run(
            ["git", "branch", "-D", info.branch],
            cwd=str(info.parent_repo),
            capture_output=True, timeout=10,
        )
    except Exception:
        pass


def list_worktrees(repo_root: Path) -> list[str]:
    """List active autocode worktrees."""
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=str(repo_root),
            capture_output=True, text=True, timeout=10,
        )
        worktrees = []
        for line in result.stdout.splitlines():
            if line.startswith("worktree ") and "autocode-wt" in line:
                worktrees.append(line.split(" ", 1)[1])
        return worktrees
    except Exception:
        return []
