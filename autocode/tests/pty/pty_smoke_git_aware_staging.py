#!/usr/bin/env python3
"""Smoke coverage for edit -> git-aware stage -> commit-message proposal.

Run: python3 autocode/tests/pty/pty_smoke_git_aware_staging.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_AUTOCODE_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_AUTOCODE_ROOT / "src"))

try:
    import dotenv  # noqa: F401
except ModuleNotFoundError:
    if os.environ.get("AUTOCODE_GIT_STAGING_SMOKE_UV") != "1":
        os.environ["AUTOCODE_GIT_STAGING_SMOKE_UV"] = "1"
        os.execvp("uv", ["uv", "run", "python3", str(Path(__file__).resolve())])
    raise

from autocode.agent.git_aware_staging import stage_post_edit  # noqa: E402

ARTIFACT_DIR = _AUTOCODE_ROOT / "docs" / "qa" / "test-results"


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, timeout=10)


def _init_repo(root: Path) -> None:
    _run(["git", "init", "-b", "main"], root)
    (root / "tracked.txt").write_text("before\n", encoding="utf-8")


def _run_smoke(root: Path) -> list[str]:
    _init_repo(root)
    (root / "tracked.txt").write_text("after\n", encoding="utf-8")

    result = stage_post_edit(["tracked.txt"], project_root=root)
    if not result.staged:
        raise AssertionError(f"expected staging success, got: {result}")
    if result.proposed_commit_message != "Update tracked.txt":
        raise AssertionError(f"unexpected proposed message: {result.proposed_commit_message}")

    staged = _run(["git", "diff", "--cached", "--name-only"], root).stdout.strip()
    if staged != "tracked.txt":
        raise AssertionError(f"expected tracked.txt staged, got: {staged!r}")

    log = _run(["git", "log", "--oneline"], root)
    if log.returncode == 0 and log.stdout.strip():
        raise AssertionError("staging smoke created an unexpected commit")

    return [
        "edited tracked.txt",
        "stage_post_edit staged tracked.txt via git add",
        f"proposed commit message: {result.proposed_commit_message}",
        "temporary repository still has no commits",
    ]


def main() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    artifact = ARTIFACT_DIR / f"{_timestamp()}-pty-smoke-git-aware-staging.md"
    try:
        with tempfile.TemporaryDirectory(prefix="autocode-git-aware-staging-") as raw:
            evidence = _run_smoke(Path(raw))
    except Exception as exc:
        artifact.write_text(
            "# Git-Aware Staging Smoke\n\n"
            "Status: FAIL\n\n"
            f"Error: `{type(exc).__name__}: {exc}`\n",
            encoding="utf-8",
        )
        print(f"[FAIL] git-aware staging smoke: {type(exc).__name__}: {exc}")
        print(f"Artifact: {artifact}")
        return 1

    artifact.write_text(
        "# Git-Aware Staging Smoke\n\n"
        "Status: PASS\n\n"
        "Scope: real temporary git repository, real edit, real git add staging, "
        "deterministic commit-message proposal, no commit created.\n\n"
        "Evidence:\n"
        + "\n".join(f"- {line}" for line in evidence)
        + "\n",
        encoding="utf-8",
    )
    print("[PASS] git-aware staging smoke")
    print(f"Artifact: {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
