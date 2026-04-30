"""Worktree isolation for subagents and risky tasks.

Based on Claude Code's worktree isolation pattern: create a
temporary git worktree for risky operations.

Uses git worktrees for lightweight isolation without full clones.
Integration back to the parent repository is user-owned: this module never
commits, merges, resets, checkouts, restores, or deletes branches.
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


@dataclass(frozen=True)
class MergeBackPlan:
    """Read-only merge-back plan for a completed worktree."""

    diff_command: list[str]
    instructions: str


def build_merge_back_plan(info: WorktreeInfo) -> MergeBackPlan:
    """Return a read-only diff command plus apply_patch handoff guidance."""
    diff_command = [
        "git",
        "diff",
        "--no-ext-diff",
        str(info.parent_repo),
        str(info.path),
    ]
    instructions = (
        "Review the diff command output, then apply accepted hunks in the main "
        "tree with the approval-gated apply_patch tool. Do not git merge/pull/checkout."
    )
    return MergeBackPlan(diff_command=diff_command, instructions=instructions)


def create_worktree(
    repo_root: Path,
    prefix: str = "autocode-wt",
) -> WorktreeInfo:
    """Create an isolated git worktree for a subagent.

    Creates a new branch and worktree in a temp location.
    The subagent works in the worktree; integration back to the parent branch
    is user-owned.
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
    """Report whether a worktree is clean enough for user-owned integration.

    Auto-merge used to live here, but commits and merges are user-owned
    operations. Return False when changes exist so callers can surface a
    proposed command sequence instead of executing it.
    """
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(info.path),
            capture_output=True, text=True, timeout=10,
        )
        return status.returncode == 0 and not status.stdout.strip()
    except Exception:
        return False


def cleanup_worktree(info: WorktreeInfo) -> None:
    """Remove a worktree path without deleting its branch."""
    try:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(info.path)],
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
