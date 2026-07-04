"""Tests for semver — inspired by vitejs/vite and langflow version checks.

Comparing version strings lexicographically is a classic harness-bench v2
pattern: "1.10.0" < "1.9.0" under string ordering, breaking any logic
that gates on minimum versions (plugin compatibility, API versioning, etc.).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_minor_double_digit_is_newer():
    from semver import is_newer
    # "1.10.0" > "1.9.0" numerically, but "1.10.0" < "1.9.0" lexicographically
    assert is_newer("1.10.0", "1.9.0") is True


def test_patch_double_digit_is_newer():
    from semver import is_newer
    assert is_newer("1.0.10", "1.0.9") is True


def test_major_is_newer():
    from semver import is_newer
    assert is_newer("2.0.0", "1.9.9") is True


def test_multi_digit_major():
    from semver import is_newer
    # "10.0.0" vs "9.0.0" — string: "1" < "9", so "10.0.0" < "9.0.0" wrongly
    assert is_newer("10.0.0", "9.0.0") is True


def test_equal_versions_not_newer():
    from semver import is_newer
    assert is_newer("1.0.0", "1.0.0") is False


def test_lower_is_not_newer():
    from semver import is_newer
    assert is_newer("1.0.0", "1.1.0") is False


def test_v_prefix_stripped():
    from semver import is_newer
    assert is_newer("v1.10.0", "v1.9.0") is True


def test_latest_picks_correct():
    from semver import latest
    versions = ["1.9.0", "1.10.0", "1.2.0"]
    assert latest(versions) == "1.10.0"
