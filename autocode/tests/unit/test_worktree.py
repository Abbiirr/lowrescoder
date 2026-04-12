"""Tests for worktree isolation."""

from __future__ import annotations

import subprocess
from pathlib import Path

from autocode.agent.worktree import (
    WorktreeInfo,
    cleanup_worktree,
    create_worktree,
    list_worktrees,
)


def _init_repo(tmp_path: Path) -> Path:
    """Create a git repo for worktree tests."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=str(repo), capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=str(repo), capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=str(repo), capture_output=True)
    (repo / "init.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "."], cwd=str(repo), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(repo), capture_output=True)
    return repo


def test_create_worktree(tmp_path: Path) -> None:
    """Create a worktree for isolation."""
    repo = _init_repo(tmp_path)
    info = create_worktree(repo)

    assert info.path.exists()
    assert info.branch.startswith("autocode/")
    assert (info.path / "init.py").exists()


def test_worktree_isolation(tmp_path: Path) -> None:
    """Changes in worktree don't affect parent."""
    repo = _init_repo(tmp_path)
    info = create_worktree(repo)

    # Write in worktree
    (info.path / "new.py").write_text("new file\n")

    # Parent should not have the file
    assert not (repo / "new.py").exists()

    cleanup_worktree(info)


def test_cleanup_worktree(tmp_path: Path) -> None:
    """Cleanup removes worktree and branch."""
    repo = _init_repo(tmp_path)
    info = create_worktree(repo)
    assert info.path.exists()

    cleanup_worktree(info)
    assert not info.path.exists()


def test_worktree_info_structure() -> None:
    """WorktreeInfo has expected fields."""
    info = WorktreeInfo(
        path=Path("/tmp/wt"),
        branch="autocode/test",
        parent_repo=Path("/repo"),
        worktree_id="test-123",
    )
    assert info.branch == "autocode/test"
    assert info.worktree_id == "test-123"
