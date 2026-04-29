"""Tests for git rollback safety — new untracked files cleaned up."""

from __future__ import annotations

import subprocess
from pathlib import Path

from autocode.agent.multi_edit import create_rollback_point, rollback


def _init_repo(tmp_path: Path) -> None:
    """Initialize a git repo with one committed file."""
    subprocess.run(["git", "init", "-b", "main"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t.com"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    subprocess.run(["git", "config", "user.name", "T"], cwd=str(tmp_path), capture_output=True)
    (tmp_path / "existing.py").write_text("original\n")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)


def test_rollback_removes_created_files(tmp_path: Path) -> None:
    """Rollback removes files that were created by the edit."""
    _init_repo(tmp_path)

    snapshot = create_rollback_point(tmp_path, files=["existing.py"])

    # Create new files (simulating what apply_multi_edit would do)
    new_file = tmp_path / "new_module.py"
    new_file.write_text("new content\n")
    new_dir = tmp_path / "sub"
    new_dir.mkdir()
    (new_dir / "deep.py").write_text("deep\n")

    # Rollback with created_files list
    success = rollback(snapshot, tmp_path, created_files=["new_module.py", "sub/deep.py"])

    assert success
    assert not new_file.exists()  # new file removed
    assert not (new_dir / "deep.py").exists()  # deep file removed
    assert (tmp_path / "existing.py").read_text() == "original\n"  # original preserved


def test_rollback_without_created_files(tmp_path: Path) -> None:
    """Rollback without created_files restores snapshotted files only."""
    _init_repo(tmp_path)

    snapshot = create_rollback_point(tmp_path, files=["existing.py"])

    # Modify tracked file
    (tmp_path / "existing.py").write_text("modified\n")

    # Create untracked file
    (tmp_path / "untracked.py").write_text("stays\n")

    # Rollback without created_files
    success = rollback(snapshot, tmp_path)

    assert success
    assert (tmp_path / "existing.py").read_text() == "original\n"  # restored
    assert (tmp_path / "untracked.py").exists()  # untracked NOT removed (safe)


def test_rollback_cleans_empty_parent_dirs(tmp_path: Path) -> None:
    """Rollback removes empty parent directories of created files."""
    _init_repo(tmp_path)

    snapshot = create_rollback_point(tmp_path, files=["existing.py"])

    # Create nested new file
    nested = tmp_path / "new_pkg" / "module.py"
    nested.parent.mkdir(parents=True)
    nested.write_text("new\n")

    success = rollback(snapshot, tmp_path, created_files=["new_pkg/module.py"])

    assert success
    assert not nested.exists()
    assert not (tmp_path / "new_pkg").exists()  # empty dir cleaned
