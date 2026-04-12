"""Typed git tools for AutoCode.

Per the deep-research-report gap analysis, raw ``run_command`` invocations of
``git`` are lossy: output parsing depends on locale, pager config, and CLI
flag variance. These wrappers expose git state as structured data so the
agent does not have to parse human-formatted output.

All tools are read-only. Mutation operations (commit/rebase/merge) stay
behind the existing ``run_command`` + approval gate because they have
irreversible consequences.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GitStatusResult:
    """Structured git status snapshot."""

    branch: str = ""
    changed: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)
    staged: list[str] = field(default_factory=list)
    ahead: int = 0
    behind: int = 0
    clean: bool = True
    error: str = ""

    def to_text(self) -> str:
        if self.error:
            return f"git_status error: {self.error}"
        lines = [f"branch: {self.branch}"]
        if self.ahead or self.behind:
            lines.append(f"ahead: {self.ahead}, behind: {self.behind}")
        if self.clean:
            lines.append("clean: working tree is clean")
            return "\n".join(lines)
        if self.staged:
            lines.append(f"staged ({len(self.staged)}):")
            for p in self.staged[:20]:
                lines.append(f"  {p}")
            if len(self.staged) > 20:
                lines.append(f"  ... and {len(self.staged) - 20} more")
        if self.changed:
            lines.append(f"changed ({len(self.changed)}):")
            for p in self.changed[:20]:
                lines.append(f"  {p}")
            if len(self.changed) > 20:
                lines.append(f"  ... and {len(self.changed) - 20} more")
        if self.untracked:
            lines.append(f"untracked ({len(self.untracked)}):")
            for p in self.untracked[:20]:
                lines.append(f"  {p}")
            if len(self.untracked) > 20:
                lines.append(f"  ... and {len(self.untracked) - 20} more")
        return "\n".join(lines)


def _run_git(
    args: list[str], *, cwd: str | Path, timeout_s: int = 10
) -> tuple[int, str, str]:
    """Run ``git`` with argv-first semantics (never a shell string).

    Returns ``(returncode, stdout, stderr)`` with a hard 10s default timeout.
    """
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except FileNotFoundError:
        return 127, "", "git binary not found on PATH"
    except subprocess.TimeoutExpired:
        return 124, "", f"git {' '.join(args)} timed out after {timeout_s}s"
    return proc.returncode, proc.stdout, proc.stderr


def git_status(project_root: str) -> GitStatusResult:
    """Return a structured git status snapshot for the given project root.

    Uses ``git status --porcelain=v1 --branch`` which is the stable
    machine-readable form documented by ``man git-status``.
    """
    result = GitStatusResult()
    rc, out, err = _run_git(
        ["status", "--porcelain=v1", "--branch", "--untracked-files=all"],
        cwd=project_root,
    )
    if rc != 0:
        result.error = err.strip() or f"git status exited {rc}"
        return result

    for line in out.splitlines():
        if not line:
            continue
        # Branch line: "## main...origin/main [ahead 2, behind 1]"
        if line.startswith("## "):
            header = line[3:]
            if "..." in header:
                result.branch = header.split("...", 1)[0]
                if "[" in header:
                    bracket = header[header.index("[") + 1 : header.rindex("]")]
                    for part in bracket.split(","):
                        part = part.strip()
                        if part.startswith("ahead "):
                            result.ahead = int(part[6:])
                        elif part.startswith("behind "):
                            result.behind = int(part[7:])
            else:
                # Detached HEAD or initial commit — header may be literal
                result.branch = header.strip()
            continue

        # Entry: XY path (X=staged, Y=worktree)
        if len(line) < 3:
            continue
        xy = line[:2]
        path = line[3:]
        if xy == "??":
            result.untracked.append(path)
            continue
        if xy[0] != " " and xy[0] != "?":
            result.staged.append(path)
        if xy[1] != " " and xy[1] != "?":
            result.changed.append(path)

    result.clean = not (result.changed or result.untracked or result.staged)
    return result


def git_diff(
    project_root: str,
    *,
    paths: list[str] | None = None,
    staged: bool = False,
    context_lines: int = 3,
    max_bytes: int = 32_768,
) -> str:
    """Return a unified diff, truncated at ``max_bytes`` to cap tokens."""
    args = ["diff", f"--unified={context_lines}"]
    if staged:
        args.append("--cached")
    if paths:
        args.append("--")
        args.extend(paths)
    rc, out, err = _run_git(args, cwd=project_root, timeout_s=15)
    if rc != 0:
        return f"git_diff error: {err.strip() or rc}"
    if len(out) > max_bytes:
        return out[:max_bytes] + f"\n[...truncated at {max_bytes} bytes, {len(out) - max_bytes} more]"
    return out or "(no changes)"


def git_log(
    project_root: str,
    *,
    max_commits: int = 20,
    paths: list[str] | None = None,
    oneline: bool = True,
) -> str:
    """Return recent commit history, bounded by ``max_commits``."""
    max_commits = max(1, min(max_commits, 200))
    args = ["log", f"-{max_commits}"]
    if oneline:
        args.append("--oneline")
    else:
        args.append("--format=%h %ad %an  %s")
        args.append("--date=short")
    if paths:
        args.append("--")
        args.extend(paths)
    rc, out, err = _run_git(args, cwd=project_root, timeout_s=15)
    if rc != 0:
        return f"git_log error: {err.strip() or rc}"
    return out or "(no commits)"


# --- Tool handler entry points (called from tools.py registry) ---


def _handle_git_status(project_root: str = "") -> str:
    root = project_root or "."
    return git_status(root).to_text()


def _handle_git_diff(
    paths: list[str] | None = None,
    staged: bool = False,
    context_lines: int = 3,
    max_bytes: int = 32_768,
    project_root: str = "",
) -> str:
    root = project_root or "."
    return git_diff(
        root,
        paths=paths,
        staged=staged,
        context_lines=context_lines,
        max_bytes=max_bytes,
    )


def _handle_git_log(
    max_commits: int = 20,
    paths: list[str] | None = None,
    oneline: bool = True,
    project_root: str = "",
) -> str:
    root = project_root or "."
    return git_log(root, max_commits=max_commits, paths=paths, oneline=oneline)


# --- bash -lc risk detection (used by run_command hardening) ---


_ESCALATION_PATTERNS: tuple[str, ...] = (
    "bash -lc",
    "bash -c",
    "sh -c",
    "sh -lc",
    "zsh -c",
    "fish -c",
    "eval ",
    "$(",
    "`",
)


def detect_shell_escalation(command: str) -> list[str]:
    """Return a list of risk patterns present in the given command string.

    An empty list means the command does not contain any flagged shell
    escalation patterns. Used by ``run_command`` hardening to mark risky
    invocations in the output so the caller can approve them explicitly.
    """
    found: list[str] = []
    lowered = command.lower()
    for pat in _ESCALATION_PATTERNS:
        if pat in lowered:
            found.append(pat.strip())
    return sorted(set(found))
