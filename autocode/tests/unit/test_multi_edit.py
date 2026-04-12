"""Tests for multi-file editing."""

from __future__ import annotations

import subprocess
from pathlib import Path

from autocode.agent.multi_edit import (
    FileEdit,
    MultiEditPlan,
    MultiEditResult,
    apply_multi_edit,
)


def test_file_edit_new_file() -> None:
    """FileEdit detects new file creation."""
    edit = FileEdit(path="new.py", old_content="", new_content="x = 1\n")
    assert edit.is_new_file
    assert not edit.is_deletion


def test_file_edit_deletion() -> None:
    """FileEdit detects file deletion."""
    edit = FileEdit(path="old.py", old_content="x = 1\n", new_content="")
    assert edit.is_deletion
    assert not edit.is_new_file


def test_file_edit_modification() -> None:
    """FileEdit detects modification."""
    edit = FileEdit(path="app.py", old_content="x = 1\n", new_content="x = 2\n")
    assert not edit.is_new_file
    assert not edit.is_deletion
    assert edit.diff_lines >= 1


def test_multi_edit_plan_preview() -> None:
    """Preview shows all planned changes."""
    plan = MultiEditPlan(
        description="Fix two bugs",
        edits=[
            FileEdit(path="a.py", old_content="x = 1\n", new_content="x = 2\n"),
            FileEdit(path="b.py", old_content="", new_content="y = 1\n"),
        ],
    )
    preview = plan.preview()
    assert "Fix two bugs" in preview
    assert "a.py" in preview
    assert "b.py" in preview
    assert "NEW FILE" in preview
    assert "2 file(s)" in preview


def test_multi_edit_plan_counts() -> None:
    """Plan tracks file count and diff lines."""
    plan = MultiEditPlan(
        edits=[
            FileEdit(path="a.py", old_content="a\nb\n", new_content="a\nc\n"),
            FileEdit(path="b.py", old_content="", new_content="new\n"),
        ],
    )
    assert plan.file_count == 2
    assert plan.total_diff_lines >= 2


def test_apply_multi_edit_creates_files(tmp_path: Path) -> None:
    """Apply creates new files."""
    plan = MultiEditPlan(
        edits=[
            FileEdit(path="new1.py", old_content="", new_content="x = 1\n"),
            FileEdit(path="sub/new2.py", old_content="", new_content="y = 2\n"),
        ],
    )
    result = apply_multi_edit(plan, tmp_path)

    assert result.success
    assert (tmp_path / "new1.py").read_text() == "x = 1\n"
    assert (tmp_path / "sub" / "new2.py").read_text() == "y = 2\n"
    assert len(result.files_created) == 2


def test_apply_multi_edit_modifies_files(tmp_path: Path) -> None:
    """Apply modifies existing files."""
    (tmp_path / "app.py").write_text("old\n")
    plan = MultiEditPlan(
        edits=[
            FileEdit(path="app.py", old_content="old\n", new_content="new\n"),
        ],
    )
    result = apply_multi_edit(plan, tmp_path)

    assert result.success
    assert (tmp_path / "app.py").read_text() == "new\n"
    assert len(result.files_modified) == 1


def test_apply_multi_edit_deletes_files(tmp_path: Path) -> None:
    """Apply deletes files."""
    (tmp_path / "delete_me.py").write_text("bye\n")
    plan = MultiEditPlan(
        edits=[
            FileEdit(path="delete_me.py", old_content="bye\n", new_content=""),
        ],
    )
    result = apply_multi_edit(plan, tmp_path)

    assert result.success
    assert not (tmp_path / "delete_me.py").exists()
    assert len(result.files_deleted) == 1


def test_apply_multi_edit_with_rollback(tmp_path: Path) -> None:
    """Apply creates rollback point in git repo."""
    # Init git repo
    subprocess.run(["git", "init", "-b", "main"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=str(tmp_path), capture_output=True)
    (tmp_path / "init.py").write_text("init\n")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)

    plan = MultiEditPlan(
        edits=[
            FileEdit(path="new.py", old_content="", new_content="added\n"),
        ],
    )
    result = apply_multi_edit(plan, tmp_path)

    assert result.success
    assert result.rollback_sha  # rollback point created


def test_multi_edit_dirty_tree_no_capture(tmp_path: Path) -> None:
    """Rollback refuses to capture unrelated dirty changes."""
    from autocode.agent.multi_edit import create_rollback_point

    # Set up git repo with committed file
    subprocess.run(["git", "init", "-b", "main"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=str(tmp_path), capture_output=True)
    (tmp_path / "tracked.py").write_text("original\n")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)

    # Create dirty unrelated change
    (tmp_path / "tracked.py").write_text("user's unrelated edit\n")

    # Rollback with no scoped files should REFUSE (returns empty)
    sha = create_rollback_point(tmp_path)
    assert sha == ""  # Refused — dirty tree

    # Rollback with scoped files should work (only stages plan files)
    (tmp_path / "plan_target.py").write_text("plan file\n")
    sha2 = create_rollback_point(tmp_path, files=["plan_target.py"])
    # May or may not produce a commit depending on whether plan_target is tracked
    # Key assertion: tracked.py's unrelated change is NOT committed
    log = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=str(tmp_path), capture_output=True, text=True,
    )
    # tracked.py should still show as modified (not committed)
    assert "tracked.py" in log.stdout


def test_multi_edit_result_structure() -> None:
    """MultiEditResult has expected fields."""
    result = MultiEditResult(
        success=True,
        files_modified=["a.py"],
        files_created=["b.py"],
        rollback_sha="abc1234",
    )
    assert result.success
    assert len(result.files_modified) == 1
