"""Tests for the deterministic outcome verifier (G3 / §4.3)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from autocode.anvil.teacher import verifier
from autocode.anvil.teacher.schemas import OracleStrength, TestResults, VerdictLabel

# --------------------------------------------------------------------------- #
# compute_label — the normative §4.3 rule, every branch                        #
# --------------------------------------------------------------------------- #


def test_label_error_when_diff_does_not_apply() -> None:
    label = verifier.compute_label(
        diff_applies=False,
        build_passed=True,
        tests=TestResults(passed=5),
        lint_clean=True,
        types_clean=True,
    )
    assert label is VerdictLabel.ERROR


def test_label_fail_on_build_break() -> None:
    label = verifier.compute_label(
        diff_applies=True,
        build_passed=False,
        tests=TestResults(passed=5),
        lint_clean=True,
        types_clean=True,
    )
    assert label is VerdictLabel.FAIL


def test_label_fail_on_failed_test() -> None:
    label = verifier.compute_label(
        diff_applies=True,
        build_passed=True,
        tests=TestResults(passed=10, failed=1),
        lint_clean=True,
        types_clean=True,
    )
    assert label is VerdictLabel.FAIL


def test_label_fail_on_regression_even_if_no_outright_failures() -> None:
    label = verifier.compute_label(
        diff_applies=True,
        build_passed=True,
        tests=TestResults(passed=10, failed=0, regressed=1),
        lint_clean=True,
        types_clean=True,
    )
    assert label is VerdictLabel.FAIL


def test_label_partial_when_tests_pass_but_lint_dirty() -> None:
    label = verifier.compute_label(
        diff_applies=True,
        build_passed=True,
        tests=TestResults(passed=10),
        lint_clean=False,
        types_clean=True,
    )
    assert label is VerdictLabel.PARTIAL


def test_label_success_when_everything_clean() -> None:
    label = verifier.compute_label(
        diff_applies=True,
        build_passed=True,
        tests=TestResults(passed=10),
        lint_clean=True,
        types_clean=True,
    )
    assert label is VerdictLabel.SUCCESS


# --------------------------------------------------------------------------- #
# pytest output parsing                                                         #
# --------------------------------------------------------------------------- #


def test_parse_pytest_summary_mixed() -> None:
    out = "=== 11 passed, 1 failed in 0.42s ==="
    assert verifier.parse_pytest_summary(out) == (11, 1)


def test_parse_pytest_summary_errors_count_as_failed() -> None:
    out = "=== 3 passed, 2 errors in 0.1s ==="
    assert verifier.parse_pytest_summary(out) == (3, 2)


def test_parse_pytest_failures_node_ids() -> None:
    out = "FAILED tests/test_a.py::test_one\nFAILED tests/test_b.py::test_two\n"
    assert verifier.parse_pytest_failures(out) == {
        "tests/test_a.py::test_one",
        "tests/test_b.py::test_two",
    }


# --------------------------------------------------------------------------- #
# verify() orchestration with a stubbed runner                                 #
# --------------------------------------------------------------------------- #


def _stub_runner(script: dict[str, tuple[int, str]]):
    def runner(cmd: list[str], cwd: Path, timeout: int) -> tuple[int, str]:
        key = cmd[0]
        # Distinguish python build (compileall) from python tests (pytest).
        if key == "python" and "pytest" in cmd:
            key = "pytest"
        elif key == "python" and "compileall" in cmd:
            key = "build"
        return script.get(key, (0, ""))

    return runner


def test_verify_success_path(tmp_path: Path) -> None:
    prof = verifier.DEFAULT_PROFILES["python"]
    runner = _stub_runner(
        {
            "build": (0, ""),
            "pytest": (0, "=== 12 passed in 0.2s ==="),
            "ruff": (0, ""),
        }
    )
    verdict = verifier.verify(tmp_path, profile=prof, runner=runner)
    assert verdict.label == VerdictLabel.SUCCESS.value
    assert verdict.tests.passed == 12
    assert verdict.oracle_strength == OracleStrength.STRONG.value


def test_verify_fail_on_failing_tests(tmp_path: Path) -> None:
    prof = verifier.DEFAULT_PROFILES["python"]
    runner = _stub_runner(
        {
            "build": (0, ""),
            "pytest": (1, "FAILED tests/test_x.py::test_y\n=== 10 passed, 1 failed in 0.2s ==="),
            "ruff": (0, ""),
        }
    )
    verdict = verifier.verify(tmp_path, profile=prof, runner=runner)
    assert verdict.label == VerdictLabel.FAIL.value
    assert verdict.tests.failed == 1


def test_verify_regression_against_baseline(tmp_path: Path) -> None:
    prof = verifier.DEFAULT_PROFILES["python"]
    # Two failures now; one of them was already failing in the baseline.
    out = "FAILED t.py::a\nFAILED t.py::b\n=== 8 passed, 2 failed in 0.2s ==="
    runner = _stub_runner({"build": (0, ""), "pytest": (1, out), "ruff": (0, "")})
    verdict = verifier.verify(tmp_path, profile=prof, runner=runner, baseline_failures={"t.py::a"})
    assert verdict.tests.regressed == 1  # only t.py::b is new
    assert verdict.label == VerdictLabel.FAIL.value


def test_verify_error_on_unappliable_diff(tmp_path: Path) -> None:
    prof = verifier.DEFAULT_PROFILES["python"]
    runner = _stub_runner({"git": (1, "patch does not apply")})
    verdict = verifier.verify(tmp_path, diff="bogus diff", profile=prof, runner=runner)
    assert verdict.label == VerdictLabel.ERROR.value
    assert verdict.diff_applies is False


def test_verify_partial_when_lint_dirty(tmp_path: Path) -> None:
    prof = verifier.DEFAULT_PROFILES["python"]
    runner = _stub_runner(
        {"build": (0, ""), "pytest": (0, "=== 5 passed in 0.1s ==="), "ruff": (1, "E501")}
    )
    verdict = verifier.verify(tmp_path, profile=prof, runner=runner)
    assert verdict.label == VerdictLabel.PARTIAL.value


def test_verify_weak_oracle_when_no_tests(tmp_path: Path) -> None:
    prof = verifier.VerifierProfile(language="generic")  # no commands at all
    verdict = verifier.verify(tmp_path, profile=prof)
    assert verdict.oracle_strength == OracleStrength.WEAK.value
    assert verdict.label == VerdictLabel.SUCCESS.value  # nothing to fail


@pytest.mark.skipif(
    subprocess.run(["bash", "-c", "command -v python"], capture_output=True).returncode != 0,
    reason="python not on PATH",
)
def test_verify_real_subprocess_python_test(tmp_path: Path) -> None:
    """End-to-end through the real default_runner with a hermetic python 'test'."""
    prof = verifier.VerifierProfile(
        language="generic",
        test_cmd=("python", "-c", "import sys; print('=== 1 passed in 0.0s ==='); sys.exit(0)"),
    )
    verdict = verifier.verify(tmp_path, profile=prof)
    assert verdict.label == VerdictLabel.SUCCESS.value
    assert verdict.tests.passed == 1
    assert verdict.oracle_strength == OracleStrength.STRONG.value
