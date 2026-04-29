"""Git-aware staging helpers for post-edit workflows.

Per AGENTS.md, never call any tree-mutating git command. Permitted:
`git status`, `git diff`, `git log`, `git fetch`, `git add`,
`git stash list/show` (read-only), and `git worktree add/list/remove`.
Forbidden: commit/push/tag/reset/rebase/merge/pull/checkout/restore/
stash push|pop|apply/apply/clean.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

GitRunner = Callable[..., subprocess.CompletedProcess[str]]

_FORBIDDEN_OPS = {
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
_FORBIDDEN_STASH_SUBCOMMANDS = {"push", "pop", "apply"}


class ForbiddenGitOperationError(ValueError):
    """Raised when code attempts to run a forbidden git operation."""


@dataclass(frozen=True)
class StagingResult:
    """Result of post-edit staging."""

    staged: bool
    files: list[str] = field(default_factory=list)
    proposed_commit_message: str = ""
    skipped_reason: str = ""


def run_git(
    args: Sequence[str],
    *,
    project_root: Path,
    runner: GitRunner = subprocess.run,
    timeout: float = 10,
) -> subprocess.CompletedProcess[str]:
    """Run a permitted git command after validating the operation."""
    if not args:
        raise ForbiddenGitOperationError("empty git command is not allowed")
    _validate_git_args(args)
    return runner(
        ["git", *args],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def stage_post_edit(
    files: Sequence[str],
    *,
    project_root: Path,
    runner: GitRunner = subprocess.run,
) -> StagingResult:
    """Stage edited files with `git add` and propose a commit message.

    This never commits. Non-git repositories are a safe no-op.
    """
    normalized = _normalize_files(files)
    if not normalized:
        return StagingResult(staged=False, skipped_reason="no files to stage")

    inside = run_git(
        ["rev-parse", "--is-inside-work-tree"],
        project_root=project_root,
        runner=runner,
        timeout=5,
    )
    if inside.returncode != 0:
        return StagingResult(
            staged=False,
            files=normalized,
            skipped_reason="not a git repository",
        )

    add = run_git(["add", "--", *normalized], project_root=project_root, runner=runner)
    if add.returncode != 0:
        reason = (add.stderr or add.stdout or "git add failed").strip()
        return StagingResult(staged=False, files=normalized, skipped_reason=reason)

    diff = run_git(
        ["diff", "--cached", "--", *normalized],
        project_root=project_root,
        runner=runner,
    )
    message = propose_commit_message(normalized, diff.stdout or "")
    return StagingResult(
        staged=True,
        files=normalized,
        proposed_commit_message=message,
    )


def propose_commit_message(files: Sequence[str], diff: str) -> str:
    """Produce a deterministic user-owned commit-message proposal."""
    normalized = _normalize_files(files)
    if not normalized:
        return "Update working tree"
    if len(normalized) == 1:
        return f"Update {normalized[0]}"
    if len(normalized) == 2:
        return f"Update {normalized[0]} and {normalized[1]}"
    return f"Update {normalized[0]} and {len(normalized) - 1} other files"


def verification_failure_warning(files: Sequence[str]) -> str:
    """Build the future G4 warning text without performing rollback."""
    file_text = ", ".join(_normalize_files(files)) or "edited files"
    return (
        f"Verification failed after editing {file_text}. "
        "No automatic rollback was performed. Use `/rollback` to inspect "
        "available checkpoints and explicitly restore if needed."
    )


def _validate_git_args(args: Sequence[str]) -> None:
    op = args[0]
    if op in _FORBIDDEN_OPS:
        raise ForbiddenGitOperationError(f"Forbidden git operation: git {op}")
    if op == "stash" and len(args) > 1 and args[1] in _FORBIDDEN_STASH_SUBCOMMANDS:
        raise ForbiddenGitOperationError(f"Forbidden git operation: git stash {args[1]}")


def _normalize_files(files: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in files:
        value = str(raw).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized
