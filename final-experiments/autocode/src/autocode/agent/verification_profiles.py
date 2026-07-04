"""Verification profiles.

Canned formatter / linter / typechecker / test-runner bundles that can be
invoked manually (``autocode verify``), via hooks (``PostToolUse`` / ``Stop``),
or programmatically from tests. Reuses the existing
``autocode.agent.verification`` types (``CheckResult`` / ``VerifyResult``) so
profile output slots into the existing ``verify.json`` contract.

Built-in profiles:

- ``python``  — ruff format + ruff check + mypy + pytest
- ``go``      — gofmt -l + go vet + go test
- ``js``      — prettier --check + eslint + tsc --noEmit + vitest run
- ``rust``    — rustfmt --check + clippy + cargo test

Profiles are best-effort: any tool that isn't installed is reported as a
failed check rather than raising. ``fast_fail`` halts on the first failure
so subsequent (potentially expensive) checks are skipped.
"""

from __future__ import annotations

import datetime as _dt
import fnmatch
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from autocode.agent.verification import CheckResult, VerifyResult


@dataclass(frozen=True)
class VerificationProfile:
    """One verification bundle."""

    name: str
    formatter: str | None = None
    linter: str | None = None
    typechecker: str | None = None
    test_runner: str | None = None
    file_globs: list[str] = field(default_factory=list)
    timeout_s: float = 120.0

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "formatter": self.formatter,
            "linter": self.linter,
            "typechecker": self.typechecker,
            "test_runner": self.test_runner,
            "file_globs": list(self.file_globs),
            "timeout_s": self.timeout_s,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> VerificationProfile:
        def _str_or_none(key: str) -> str | None:
            value = data.get(key)
            return value if isinstance(value, str) else None

        raw_globs = data.get("file_globs") or []
        file_globs: list[str] = (
            [str(x) for x in raw_globs] if isinstance(raw_globs, (list, tuple)) else []
        )
        raw_timeout = data.get("timeout_s")
        timeout_s = (
            float(raw_timeout)
            if isinstance(raw_timeout, (int, float, str))
            else 120.0
        )

        return cls(
            name=str(data.get("name", "unnamed")),
            formatter=_str_or_none("formatter"),
            linter=_str_or_none("linter"),
            typechecker=_str_or_none("typechecker"),
            test_runner=_str_or_none("test_runner"),
            file_globs=file_globs,
            timeout_s=timeout_s,
        )


BUILTIN_PROFILES: dict[str, VerificationProfile] = {
    "python": VerificationProfile(
        name="python",
        formatter="ruff format --check",
        linter="ruff check",
        typechecker="mypy --no-error-summary",
        test_runner="pytest -q --no-header",
        file_globs=["*.py"],
    ),
    "go": VerificationProfile(
        name="go",
        formatter="gofmt -l .",
        linter="go vet ./...",
        typechecker=None,  # Go has no separate typechecker
        test_runner="go test -count=1 ./...",
        file_globs=["*.go"],
    ),
    "js": VerificationProfile(
        name="js",
        formatter="prettier --check .",
        linter="eslint .",
        typechecker="tsc --noEmit",
        test_runner="vitest run",
        file_globs=["*.js", "*.jsx", "*.ts", "*.tsx"],
    ),
    "rust": VerificationProfile(
        name="rust",
        formatter="rustfmt --check",
        linter="cargo clippy --all-targets -- -D warnings",
        typechecker=None,
        test_runner="cargo test",
        file_globs=["*.rs"],
    ),
}


def profile_names() -> list[str]:
    """Return the ordered list of built-in profile names."""
    return list(BUILTIN_PROFILES.keys())


def load_profile(name: str) -> VerificationProfile | None:
    """Look up a built-in profile by name; returns None if unknown."""
    return BUILTIN_PROFILES.get(name)


def select_profile_for_files(
    changed_files: list[Path],
) -> VerificationProfile | None:
    """Pick the profile whose file_globs match any of the changed files.

    Returns None if no profile matches or the list is empty. First-match
    wins in built-in definition order.
    """
    if not changed_files:
        return None
    for profile in BUILTIN_PROFILES.values():
        for changed in changed_files:
            for glob in profile.file_globs:
                if fnmatch.fnmatch(changed.name, glob):
                    return profile
    return None


def run_profile(
    profile: VerificationProfile,
    changed_files: list[Path],
    *,
    cwd: Path,
    fast_fail: bool = False,
) -> VerifyResult:
    """Run every configured check in the profile against ``cwd``.

    Empty ``changed_files`` short-circuits to a vacuous success (no checks).
    ``fast_fail=True`` stops at the first non-zero exit so subsequent
    (potentially slow) checks don't waste time.
    """
    timestamp = _dt.datetime.now(tz=_dt.UTC).isoformat()
    result = VerifyResult(timestamp=timestamp)

    if not changed_files:
        result.all_passed = True
        return result

    commands: list[tuple[str, str | None]] = [
        ("formatter", profile.formatter),
        ("linter", profile.linter),
        ("typechecker", profile.typechecker),
        ("test_runner", profile.test_runner),
    ]

    start = time.monotonic()
    all_passed = True
    for slot, cmd in commands:
        if cmd is None:
            continue
        check = _run_check(slot, cmd, cwd=cwd, timeout_s=profile.timeout_s)
        result.checks.append(check)
        if not check.passed:
            all_passed = False
            if fast_fail:
                break

    result.total_duration_ms = int((time.monotonic() - start) * 1000)
    result.all_passed = all_passed and bool(result.checks)
    return result


def _run_check(
    name: str,
    command: str,
    *,
    cwd: Path,
    timeout_s: float,
) -> CheckResult:
    start = time.monotonic()
    try:
        proc = subprocess.run(  # noqa: S602 — user-authored tool commands by design
            command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - start) * 1000)
        return CheckResult(
            name=name,
            command=command,
            exit_code=-1,
            duration_ms=duration_ms,
            summary=f"timeout after {timeout_s}s",
        )
    except (OSError, ValueError) as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        return CheckResult(
            name=name,
            command=command,
            exit_code=-2,
            duration_ms=duration_ms,
            summary=str(exc),
        )
    duration_ms = int((time.monotonic() - start) * 1000)
    out = proc.stdout.decode("utf-8", errors="replace")
    err = proc.stderr.decode("utf-8", errors="replace")
    summary = (out + err).strip()[:2000]
    return CheckResult(
        name=name,
        command=command,
        exit_code=proc.returncode,
        duration_ms=duration_ms,
        summary=summary,
    )


__all__ = [
    "BUILTIN_PROFILES",
    "VerificationProfile",
    "load_profile",
    "profile_names",
    "run_profile",
    "select_profile_for_files",
]
