"""Stable TUI v1 Slice 6 — tests for verification profiles (Milestone F).

Built-in profiles run formatter + linter + typechecker + test-runner against
changed files and produce a `VerifyResult`. Profiles are hook-addressable so
they can fire automatically at PostToolUse / Stop.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from autocode.agent.verification_profiles import (
    VerificationProfile,
    load_profile,
    profile_names,
    run_profile,
    select_profile_for_files,
)


def test_builtin_profiles_exist() -> None:
    names = profile_names()
    assert "python" in names
    assert "go" in names
    assert "js" in names
    assert "rust" in names


def test_python_profile_fields() -> None:
    profile = load_profile("python")
    assert profile.name == "python"
    assert profile.linter is not None
    assert "ruff" in profile.linter
    assert profile.test_runner is not None
    assert any("*.py" in g for g in profile.file_globs)


def test_go_profile_fields() -> None:
    profile = load_profile("go")
    assert profile.name == "go"
    assert profile.test_runner is not None
    assert "go test" in profile.test_runner


def test_load_profile_unknown_returns_none() -> None:
    assert load_profile("nonexistent-language") is None


def test_select_profile_for_python_files(tmp_path: Path) -> None:
    py1 = tmp_path / "app.py"
    py1.touch()
    profile = select_profile_for_files([py1])
    assert profile is not None
    assert profile.name == "python"


def test_select_profile_for_go_files(tmp_path: Path) -> None:
    go1 = tmp_path / "main.go"
    go1.touch()
    profile = select_profile_for_files([go1])
    assert profile is not None
    assert profile.name == "go"


def test_select_profile_empty_returns_none() -> None:
    assert select_profile_for_files([]) is None


def test_select_profile_unknown_extension_returns_none(tmp_path: Path) -> None:
    f = tmp_path / "data.xyz"
    f.touch()
    assert select_profile_for_files([f]) is None


def test_run_profile_empty_changed_files_returns_skipped(tmp_path: Path) -> None:
    profile = load_profile("python")
    assert profile is not None
    result = run_profile(profile, changed_files=[], cwd=tmp_path)
    # No checks run, all_passed vacuous-true
    assert result.all_passed is True
    assert len(result.checks) == 0


def test_run_profile_fast_fail_when_linter_fails(tmp_path: Path) -> None:
    # Create a profile that fails immediately
    profile = VerificationProfile(
        name="fail-demo",
        formatter=None,
        linter="false",  # exits 1
        typechecker="echo should_not_run",
        test_runner="echo should_not_run",
        file_globs=["*.py"],
    )
    changed = [tmp_path / "a.py"]
    (tmp_path / "a.py").touch()
    result = run_profile(profile, changed_files=changed, cwd=tmp_path, fast_fail=True)
    assert result.all_passed is False
    # Only the linter runs
    assert len(result.checks) == 1
    assert result.checks[0].exit_code != 0


def test_run_profile_writes_verify_json(tmp_path: Path) -> None:
    profile = VerificationProfile(
        name="echo-demo",
        formatter=None,
        linter="true",
        typechecker=None,
        test_runner="true",
        file_globs=["*.py"],
    )
    changed = [tmp_path / "a.py"]
    (tmp_path / "a.py").touch()
    out_path = tmp_path / "verify.json"
    result = run_profile(profile, changed_files=changed, cwd=tmp_path)
    result.write_to(out_path)
    assert out_path.is_file()


def test_run_profile_results_include_durations(tmp_path: Path) -> None:
    profile = VerificationProfile(
        name="timed-demo",
        formatter=None,
        linter="true",
        typechecker=None,
        test_runner=None,
        file_globs=["*.py"],
    )
    (tmp_path / "x.py").touch()
    result = run_profile(profile, changed_files=[tmp_path / "x.py"], cwd=tmp_path)
    assert result.total_duration_ms >= 0
    assert all(check.duration_ms >= 0 for check in result.checks)


def test_profile_serializes_to_dict() -> None:
    profile = load_profile("python")
    assert profile is not None
    data = profile.to_dict()
    assert data["name"] == "python"
    assert "file_globs" in data


def test_profile_from_dict_roundtrip() -> None:
    profile = load_profile("python")
    assert profile is not None
    data = profile.to_dict()
    restored = VerificationProfile.from_dict(data)
    assert restored.name == profile.name
    assert restored.file_globs == profile.file_globs


@pytest.mark.parametrize(
    "language", ["python", "go", "js", "rust"],
)
def test_each_builtin_profile_has_at_least_one_check(language: str) -> None:
    profile = load_profile(language)
    assert profile is not None
    checks = [
        profile.formatter,
        profile.linter,
        profile.typechecker,
        profile.test_runner,
    ]
    assert any(c for c in checks), f"{language} has no checks configured"


def test_run_profile_propagates_cwd(tmp_path: Path) -> None:
    """Verify that cwd is honored by the profile runner."""
    profile = VerificationProfile(
        name="pwd-demo",
        formatter=None,
        linter="pwd",  # prints cwd
        typechecker=None,
        test_runner=None,
        file_globs=["*"],
    )
    marker = tmp_path / "marker.txt"
    marker.touch()
    result = run_profile(profile, changed_files=[marker], cwd=tmp_path)
    # linter summary should include tmp_path
    assert any(str(tmp_path) in c.summary for c in result.checks)
