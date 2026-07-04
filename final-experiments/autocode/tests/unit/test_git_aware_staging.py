"""Tests for git-aware post-edit staging."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest


def _completed(args: list[str], returncode: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(
        args=args,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


class RecordingRunner:
    def __init__(self, *, in_git_repo: bool = True) -> None:
        self.calls: list[list[str]] = []
        self.in_git_repo = in_git_repo

    def __call__(self, args: list[str], **kwargs):
        self.calls.append(args)
        if args[:3] == ["git", "rev-parse", "--is-inside-work-tree"]:
            return _completed(args, 0 if self.in_git_repo else 128, "true\n")
        if args[:2] == ["git", "add"]:
            return _completed(args, 0, "")
        if args[:3] == ["git", "diff", "--cached"]:
            return _completed(args, 0, "diff --git a/app.py b/app.py\n")
        return _completed(args, 0, "")


def test_stage_post_edit_stages_files_and_proposes_commit_message(tmp_path: Path) -> None:
    from autocode.agent.git_aware_staging import stage_post_edit

    runner = RecordingRunner()
    result = stage_post_edit(["app.py"], project_root=tmp_path, runner=runner)

    assert result.staged is True
    assert result.skipped_reason == ""
    assert "app.py" in result.proposed_commit_message
    assert ["git", "add", "--", "app.py"] in runner.calls
    assert not any(call[1] in {"commit", "reset", "checkout", "restore"} for call in runner.calls)


def test_stage_post_edit_noops_outside_git_repo(tmp_path: Path) -> None:
    from autocode.agent.git_aware_staging import stage_post_edit

    runner = RecordingRunner(in_git_repo=False)
    result = stage_post_edit(["app.py"], project_root=tmp_path, runner=runner)

    assert result.staged is False
    assert "not a git repository" in result.skipped_reason
    assert not any(call[:2] == ["git", "add"] for call in runner.calls)


@pytest.mark.parametrize(
    "args",
    [
        ["commit", "-m", "x"],
        ["push"],
        ["tag", "v1"],
        ["reset", "--hard"],
        ["rebase", "main"],
        ["merge", "main"],
        ["pull"],
        ["checkout", "main"],
        ["restore", "file.py"],
        ["stash", "push"],
        ["stash", "pop"],
        ["stash", "apply"],
        ["apply", "patch.diff"],
        ["clean", "-fd"],
    ],
)
def test_run_git_blocks_forbidden_operations(tmp_path: Path, args: list[str]) -> None:
    from autocode.agent.git_aware_staging import ForbiddenGitOperationError, run_git

    with pytest.raises(ForbiddenGitOperationError):
        run_git(args, project_root=tmp_path, runner=RecordingRunner())


def test_propose_commit_message_is_deterministic() -> None:
    from autocode.agent.git_aware_staging import propose_commit_message

    message = propose_commit_message(
        ["src/app.py", "tests/test_app.py"],
        "diff --git a/src/app.py b/src/app.py\n",
    )

    assert message == "Update src/app.py and tests/test_app.py"


def test_verification_failure_warning_offers_rollback_without_auto_revert() -> None:
    from autocode.agent.git_aware_staging import verification_failure_warning

    warning = verification_failure_warning(["src/app.py"])

    assert "/rollback" in warning
    assert "No automatic rollback was performed" in warning


def test_git_aware_staging_source_does_not_invoke_forbidden_git_ops() -> None:
    source = Path("autocode/src/autocode/agent/git_aware_staging.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    forbidden = {
        "commit",
        "push",
        "tag",
        "reset",
        "rebase",
        "merge",
        "pull",
        "checkout",
        "restore",
        "clean",
        "apply",
    }

    for node in ast.walk(tree):
        if not isinstance(node, ast.List):
            continue
        values = [elt.value for elt in node.elts if isinstance(elt, ast.Constant)]
        if values and values[0] == "git":
            assert not any(value in forbidden for value in values[1:])


def test_product_source_does_not_invoke_forbidden_git_ops() -> None:
    """Product code must not run user-owned destructive git operations."""
    root = Path("autocode/src/autocode")
    forbidden_seen: list[str] = []
    forbidden_ops = {
        "commit",
        "push",
        "tag",
        "reset",
        "rebase",
        "merge",
        "pull",
        "checkout",
        "restore",
        "apply",
        "clean",
    }
    forbidden_stash_ops = {"push", "pop", "apply"}

    for path in root.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.List):
                continue
            values = [
                elt.value
                for elt in node.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            ]
            if len(values) < 2 or values[0] != "git":
                continue
            op = values[1]
            if op in forbidden_ops:
                forbidden_seen.append(f"{path}: git {' '.join(values[1:])}")
            if op == "stash" and len(values) > 2 and values[2] in forbidden_stash_ops:
                forbidden_seen.append(f"{path}: git {' '.join(values[1:])}")

    assert forbidden_seen == []
