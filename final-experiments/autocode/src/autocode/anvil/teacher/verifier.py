"""The deterministic outcome verifier (G3, §4.3) — the teacher's executable oracle.

The verifier is the *oracle*: every teaching decision ultimately references its
verdict (PLAN_04 §0.3.1). It applies a candidate diff to a repo, then runs the
deterministic checks (build → tests → lint → types) and emits a :class:`Verdict`
with the normative ``label``.

Design notes
------------
* The **label logic** (:func:`compute_label`) is a pure function — it is the
  normative §4.3 rule and is unit-tested in isolation.
* Command execution goes through an injectable :data:`CommandRunner`, so the
  orchestration is testable without a real toolchain, and so different sandboxes
  (host, Docker) can plug in their own launcher — the same seam the benchmarks
  and harness-tester rigs already use.
* ``regressed`` is only meaningful against a baseline: pass ``baseline_failures``
  (the set of test ids failing *before* the diff) and any newly-failing test is
  counted as a regression — an automatic FAIL (§2).
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from autocode.anvil.teacher.schemas import (
    OracleStrength,
    TestResults,
    Verdict,
    VerdictLabel,
)

# (cmd, cwd, timeout) -> (returncode, combined_output)
CommandRunner = Callable[[list[str], Path, int], tuple[int, str]]


def default_runner(cmd: list[str], cwd: Path, timeout: int) -> tuple[int, str]:
    """Run ``cmd`` in ``cwd``; return (returncode, last-4k-of-combined-output)."""
    try:
        proc = subprocess.run(  # noqa: S603 - caller-provided fixed command list
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return 127, f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timeout after {timeout}s: {' '.join(cmd)}"
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or ""))[-4000:]


@dataclass(frozen=True)
class VerifierProfile:
    """Per-language check commands. An empty list means "skip / pass by default"."""

    language: str
    build_cmd: tuple[str, ...] = ()
    test_cmd: tuple[str, ...] = ()
    lint_cmd: tuple[str, ...] = ()
    types_cmd: tuple[str, ...] = ()
    timeout_s: int = 600


# Sensible defaults; the loop/CLI can override per repo via .autocode config.
DEFAULT_PROFILES: dict[str, VerifierProfile] = {
    "python": VerifierProfile(
        language="python",
        build_cmd=("python", "-m", "compileall", "-q", "."),
        test_cmd=("python", "-m", "pytest", "-q"),
        lint_cmd=("ruff", "check", "."),
        types_cmd=(),  # mypy is opt-in; off by default to avoid noisy weak signals
    ),
    "generic": VerifierProfile(language="generic"),
}


_PYTEST_SUMMARY = re.compile(
    r"(?:(?P<passed>\d+)\s+passed)|(?:(?P<failed>\d+)\s+failed)|(?:(?P<errors>\d+)\s+error)"
)
_PYTEST_FAIL_ID = re.compile(r"^FAILED\s+(\S+)", re.MULTILINE)


def parse_pytest_summary(output: str) -> tuple[int, int]:
    """Parse pytest's terminal summary into (passed, failed+errors). Best-effort."""
    passed = failed = 0
    for m in _PYTEST_SUMMARY.finditer(output):
        if m.group("passed"):
            passed = int(m.group("passed"))
        if m.group("failed"):
            failed += int(m.group("failed"))
        if m.group("errors"):
            failed += int(m.group("errors"))
    return passed, failed


def parse_pytest_failures(output: str) -> set[str]:
    """Extract the set of failing test node ids from pytest output."""
    return set(_PYTEST_FAIL_ID.findall(output))


def compute_label(
    *,
    diff_applies: bool,
    build_passed: bool,
    tests: TestResults,
    lint_clean: bool,
    types_clean: bool,
) -> VerdictLabel:
    """The normative §4.3 label rule. Order matters; this is the signal hierarchy.

    * ``error``  — the diff would not even apply.
    * ``fail``   — build broke, or any test failed, or anything *regressed*.
    * ``partial``— code builds and tests pass, but lint/types are not clean.
    * ``success``— everything above is clean.
    """
    if not diff_applies:
        return VerdictLabel.ERROR
    if not build_passed:
        return VerdictLabel.FAIL
    if tests.failed > 0 or tests.regressed > 0:
        return VerdictLabel.FAIL
    if not (lint_clean and types_clean):
        return VerdictLabel.PARTIAL
    return VerdictLabel.SUCCESS


def _git_apply(diff_text: str, repo: Path, runner: CommandRunner, timeout: int) -> bool:
    """Return True iff ``diff_text`` applies cleanly to ``repo`` (and apply it)."""
    patch = repo / ".anvil_candidate.patch"
    try:
        patch.write_text(diff_text, encoding="utf-8")
        rc_check, _ = runner(["git", "apply", "--check", str(patch)], repo, timeout)
        if rc_check != 0:
            # Fall back to 3-way for context drift.
            rc_check, _ = runner(["git", "apply", "--3way", "--check", str(patch)], repo, timeout)
            if rc_check != 0:
                return False
        rc_apply, _ = runner(["git", "apply", "--3way", str(patch)], repo, timeout)
        return rc_apply == 0
    finally:
        patch.unlink(missing_ok=True)


def verify(
    repo_dir: str | Path,
    *,
    diff: str | None = None,
    profile: VerifierProfile | None = None,
    runner: CommandRunner | None = None,
    baseline_failures: Iterable[str] | None = None,
) -> Verdict:
    """Apply ``diff`` (if any) to ``repo_dir`` and run the deterministic checks.

    Returns a :class:`Verdict`. ``diff is None`` means the working tree already
    holds the candidate change (``diff_applies`` is then vacuously True).
    """
    repo = Path(repo_dir)
    prof = profile or DEFAULT_PROFILES["generic"]
    run = runner or default_runner
    baseline = set(baseline_failures or ())

    # 1. diff applies?
    diff_applies = True
    if diff is not None and diff.strip():
        diff_applies = _git_apply(diff, repo, run, prof.timeout_s)
    if not diff_applies:
        return Verdict(
            diff_applies=False,
            build_passed=False,
            tests=TestResults(),
            lint_clean=False,
            types_clean=False,
            label=VerdictLabel.ERROR.value,
            oracle_strength=OracleStrength.STRONG.value,
        )

    # 2. build (empty command => pass by default, e.g. interpreted langs w/o build)
    build_passed = True
    if prof.build_cmd:
        rc, _ = run(list(prof.build_cmd), repo, prof.timeout_s)
        build_passed = rc == 0

    # 3. tests
    tests = TestResults()
    ran_tests = False
    if prof.test_cmd:
        rc, out = run(list(prof.test_cmd), repo, prof.timeout_s)
        ran_tests = True
        passed, failed = parse_pytest_summary(out)
        # If parsing found nothing, fall back to the return code.
        if passed == 0 and failed == 0:
            if rc == 0:
                passed = 1  # at least it ran clean
            else:
                failed = 1
        now_failing = parse_pytest_failures(out)
        regressed = len(now_failing - baseline) if baseline else 0
        tests = TestResults(passed=passed, failed=failed, regressed=regressed)

    # 4. lint / types (empty command => clean by default)
    lint_clean = True
    if prof.lint_cmd:
        rc, _ = run(list(prof.lint_cmd), repo, prof.timeout_s)
        lint_clean = rc == 0
    types_clean = True
    if prof.types_cmd:
        rc, _ = run(list(prof.types_cmd), repo, prof.timeout_s)
        types_clean = rc == 0

    label = compute_label(
        diff_applies=diff_applies,
        build_passed=build_passed,
        tests=tests,
        lint_clean=lint_clean,
        types_clean=types_clean,
    )
    strength = OracleStrength.STRONG if ran_tests else OracleStrength.WEAK
    return Verdict(
        diff_applies=diff_applies,
        build_passed=build_passed,
        tests=tests,
        lint_clean=lint_clean,
        types_clean=types_clean,
        label=label.value,
        oracle_strength=strength.value,
    )


__all__ = [
    "CommandRunner",
    "default_runner",
    "VerifierProfile",
    "DEFAULT_PROFILES",
    "parse_pytest_summary",
    "parse_pytest_failures",
    "compute_label",
    "verify",
]
