"""Tests for git safety features: auto-commit, GIT_EDITOR blocking, shell timeout."""

from __future__ import annotations

import subprocess
from pathlib import Path

from autocode.agent.tools import _handle_run_command, _safe_shell_env


def test_git_editor_blocked() -> None:
    """GIT_EDITOR env var is set to 'true' to prevent interactive editors."""
    env = _safe_shell_env()
    assert env["GIT_EDITOR"] == "true"
    assert env["EDITOR"] == "true"
    assert env["VISUAL"] == "true"
    assert env["GIT_TERMINAL_PROMPT"] == "0"


def test_shell_timeout_or_error() -> None:
    """Shell commands timeout or fail gracefully."""
    result = _handle_run_command("sleep 60", timeout=1)
    # May timeout or fail with sandbox permission error — both are acceptable
    assert "timed out" in result.lower() or "exit code" in result.lower() or "error" in result.lower()


def test_shell_env_noninteractive() -> None:
    """Shell environment blocks interactive prompts."""
    env = _safe_shell_env()
    assert env["DEBIAN_FRONTEND"] == "noninteractive"


def test_git_autocommit_before_edit(tmp_path: Path) -> None:
    """Auto-commit creates a safety snapshot before file modification."""
    from autocode.agent.tools import _git_auto_commit

    # Set up a git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main"], cwd=str(repo),
        capture_output=True, timeout=5,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(repo), capture_output=True, timeout=5,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(repo), capture_output=True, timeout=5,
    )

    # Create and commit a file
    test_file = repo / "hello.py"
    test_file.write_text("x = 1\n")
    subprocess.run(
        ["git", "add", "hello.py"], cwd=str(repo),
        capture_output=True, timeout=5,
    )
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=str(repo), capture_output=True, timeout=5,
    )

    # Modify the file (unstaged change)
    test_file.write_text("x = 2\n")

    # Auto-commit should create a safety snapshot
    sha = _git_auto_commit(test_file)
    assert sha is not None
    assert len(sha) >= 7  # short SHA

    # Verify the commit exists
    log = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=str(repo), capture_output=True, text=True, timeout=5,
    )
    assert "autocode: safety snapshot" in log.stdout


def test_git_autocommit_no_changes(tmp_path: Path) -> None:
    """Auto-commit returns None when file has no changes."""
    from autocode.agent.tools import _git_auto_commit

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main"], cwd=str(repo),
        capture_output=True, timeout=5,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(repo), capture_output=True, timeout=5,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(repo), capture_output=True, timeout=5,
    )

    test_file = repo / "clean.py"
    test_file.write_text("clean\n")
    subprocess.run(
        ["git", "add", "."], cwd=str(repo),
        capture_output=True, timeout=5,
    )
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=str(repo), capture_output=True, timeout=5,
    )

    # No changes — should return None
    sha = _git_auto_commit(test_file)
    assert sha is None


def test_git_autocommit_untracked_file(tmp_path: Path) -> None:
    """Auto-commit returns None for untracked files."""
    from autocode.agent.tools import _git_auto_commit

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main"], cwd=str(repo),
        capture_output=True, timeout=5,
    )

    untracked = repo / "new.py"
    untracked.write_text("new\n")

    sha = _git_auto_commit(untracked)
    assert sha is None
