"""Tests for typed git tools (deep-research-report Lane A)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from autocode.agent.git_tools import (
    detect_shell_escalation,
    git_diff,
    git_log,
    git_status,
)


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """Initialize a minimal git repo with one committed file."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "config", "commit.gpgsign", "false")
    (tmp_path / "README.md").write_text("# hello\n")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-qm", "initial")
    return tmp_path


class TestGitStatus:
    def test_clean_repo(self, repo: Path) -> None:
        result = git_status(str(repo))
        assert result.clean is True
        assert result.branch  # some branch name
        assert result.changed == []
        assert result.untracked == []
        assert result.error == ""

    def test_untracked_file(self, repo: Path) -> None:
        (repo / "new.txt").write_text("x")
        result = git_status(str(repo))
        assert result.clean is False
        assert "new.txt" in result.untracked

    def test_modified_file(self, repo: Path) -> None:
        (repo / "README.md").write_text("# changed\n")
        result = git_status(str(repo))
        assert result.clean is False
        assert "README.md" in result.changed

    def test_staged_file(self, repo: Path) -> None:
        (repo / "README.md").write_text("# staged\n")
        _git(repo, "add", "README.md")
        result = git_status(str(repo))
        assert "README.md" in result.staged

    def test_non_repo_returns_error(self, tmp_path: Path) -> None:
        not_a_repo = tmp_path / "empty"
        not_a_repo.mkdir()
        result = git_status(str(not_a_repo))
        assert result.error

    def test_to_text_clean(self, repo: Path) -> None:
        text = git_status(str(repo)).to_text()
        assert "clean" in text
        assert "branch:" in text

    def test_to_text_dirty(self, repo: Path) -> None:
        (repo / "a.txt").write_text("1")
        text = git_status(str(repo)).to_text()
        assert "untracked" in text
        assert "a.txt" in text


class TestGitDiff:
    def test_no_changes(self, repo: Path) -> None:
        assert git_diff(str(repo)) == "(no changes)"

    def test_working_tree_change(self, repo: Path) -> None:
        (repo / "README.md").write_text("# hello\nplus more\n")
        out = git_diff(str(repo))
        assert "plus more" in out
        assert "README.md" in out

    def test_staged_flag(self, repo: Path) -> None:
        (repo / "README.md").write_text("# staged change\n")
        _git(repo, "add", "README.md")
        # Working tree is clean now (change is staged)
        assert git_diff(str(repo)) == "(no changes)"
        staged_out = git_diff(str(repo), staged=True)
        assert "staged change" in staged_out

    def test_max_bytes_truncation(self, repo: Path) -> None:
        # Create a file with varied content so the diff is large after rewrite
        (repo / "big.txt").write_text("\n".join(f"line {i}" for i in range(500)) + "\n")
        _git(repo, "add", "big.txt")
        _git(repo, "commit", "-qm", "add big")
        # Completely rewrite — produces a diff with 500 removals + 500 additions
        (repo / "big.txt").write_text("\n".join(f"CHANGED {i}" for i in range(500)) + "\n")
        out = git_diff(str(repo), max_bytes=200)
        assert "truncated" in out
        assert len(out) <= 300  # 200 bytes + truncation marker


class TestGitLog:
    def test_single_commit(self, repo: Path) -> None:
        out = git_log(str(repo))
        assert "initial" in out

    def test_max_commits_cap(self, repo: Path) -> None:
        for i in range(5):
            (repo / f"f{i}.txt").write_text(str(i))
            _git(repo, "add", f"f{i}.txt")
            _git(repo, "commit", "-qm", f"commit {i}")
        out = git_log(str(repo), max_commits=2)
        lines = [ln for ln in out.splitlines() if ln.strip()]
        assert len(lines) == 2

    def test_oneline_false(self, repo: Path) -> None:
        out = git_log(str(repo), oneline=False)
        assert "initial" in out


class TestShellEscalationDetection:
    def test_plain_command_has_no_escalation(self) -> None:
        assert detect_shell_escalation("ls -la") == []
        assert detect_shell_escalation("git status") == []
        assert detect_shell_escalation("python script.py") == []

    def test_bash_lc_flagged(self) -> None:
        result = detect_shell_escalation("bash -lc 'echo hi'")
        assert "bash -lc" in result

    def test_sh_c_flagged(self) -> None:
        result = detect_shell_escalation("sh -c 'echo hi'")
        assert "sh -c" in result

    def test_eval_flagged(self) -> None:
        result = detect_shell_escalation("eval $(cat script.sh)")
        # eval AND $( should both be flagged
        assert "eval" in result
        assert "$(" in result

    def test_backtick_flagged(self) -> None:
        result = detect_shell_escalation("echo `whoami`")
        assert "`" in result

    def test_command_substitution_flagged(self) -> None:
        result = detect_shell_escalation("echo $(whoami)")
        assert "$(" in result
