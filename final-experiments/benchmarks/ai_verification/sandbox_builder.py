"""Sandbox repo builder for AI verification runs.

Creates an isolated throwaway repo under sandboxes/ai-verification/<run_id>/
from a ScenarioSpec's repo_seed configuration.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from benchmarks.ai_verification.schema import (
    Injection,
    RepoSeed,
    SeedMode,
    FIXTURES_DIR,
)


def build_sandbox(repo_seed: RepoSeed, sandbox_path: Path) -> None:
    """Create the sandbox repo from repo_seed. Raises on any failure."""
    sandbox_path.mkdir(parents=True, exist_ok=True)

    if repo_seed.mode in (SeedMode.FIXTURE, SeedMode.MUTATE):
        if not repo_seed.fixture_ref:
            raise ValueError("fixture_ref required for FIXTURE/MUTATE seed mode")
        fixture_src = FIXTURES_DIR / repo_seed.fixture_ref
        if not fixture_src.is_dir():
            raise FileNotFoundError(f"Fixture not found: {fixture_src}")
        _copy_fixture(fixture_src, sandbox_path)

    for injection in repo_seed.injections:
        _apply_injection(injection, sandbox_path)

    _git_init(sandbox_path)

    for cmd in repo_seed.setup_commands:
        _run(cmd, cwd=sandbox_path)


def snapshot_repo(sandbox_path: Path, snapshot_dir: Path) -> None:
    """Copy current sandbox state into snapshot_dir (pre-agent snapshot)."""
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)
    shutil.copytree(
        sandbox_path,
        snapshot_dir,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".venv"),
    )


def teardown_sandbox(sandbox_path: Path) -> None:
    """Remove sandbox. Called after artifact capture."""
    if sandbox_path.exists():
        shutil.rmtree(sandbox_path)


def _copy_fixture(src: Path, dst: Path) -> None:
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def _apply_injection(injection: Injection, sandbox_path: Path) -> None:
    injection_path = Path(injection.path)
    if injection_path.is_absolute():
        raise ValueError(f"injection path must be relative: {injection.path!r}")

    sandbox_root = sandbox_path.resolve()
    target = (sandbox_path / injection_path).resolve()
    try:
        target.relative_to(sandbox_root)
    except ValueError as exc:
        raise ValueError(f"injection path escapes sandbox: {injection.path!r}") from exc

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(injection.content, encoding="utf-8")


def _git_init(sandbox_path: Path) -> None:
    _run("git init -q", cwd=sandbox_path)
    _run("git config user.email ci@ai-verification.local", cwd=sandbox_path)
    _run("git config user.name 'AI Verification'", cwd=sandbox_path)
    # For fresh/empty repos there may be nothing to stage — write a marker so the
    # initial commit always succeeds.
    marker = sandbox_path / ".scenario_seed"
    if not any(p for p in sandbox_path.iterdir() if p.name != ".git"):
        marker.write_text("", encoding="utf-8")
    _run("git add -A", cwd=sandbox_path)
    _run("git commit -q -m 'scenario seed'", cwd=sandbox_path)


def _run(cmd: str, cwd: Path) -> None:
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Setup command failed: {cmd!r}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
