"""Tests for release_sorter — inspired by go-gitea/gitea release listing.

Gitea lists releases sorted by semantic version, newest first. The bug uses
Python's default string sort, which sorts lexicographically. This means
'v1.10.0' < 'v1.9.0' (because '1' < '9'), so v1.10.0 appears AFTER v1.9.0.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_major_version_sort():
    from release_sorter import sort_releases
    result = sort_releases(["v1.0.0", "v2.0.0"])
    assert result == ["v2.0.0", "v1.0.0"]


def test_patch_version_sort():
    from release_sorter import sort_releases
    result = sort_releases(["v1.0.1", "v1.0.2"])
    assert result == ["v1.0.2", "v1.0.1"]


def test_already_sorted_unchanged():
    from release_sorter import sort_releases
    result = sort_releases(["v3.0.0", "v2.0.0", "v1.0.0"])
    assert result == ["v3.0.0", "v2.0.0", "v1.0.0"]


def test_single_tag():
    from release_sorter import sort_releases
    assert sort_releases(["v1.0.0"]) == ["v1.0.0"]


def test_double_digit_minor_newest_first():
    from release_sorter import sort_releases
    # Bug: lex gives ["v1.9.0", "v1.10.0"]; expected: ["v1.10.0", "v1.9.0"]
    result = sort_releases(["v1.9.0", "v1.10.0"])
    assert result == ["v1.10.0", "v1.9.0"], (
        f"expected ['v1.10.0', 'v1.9.0'] (semver), got {result}"
    )


def test_double_digit_patch_newest_first():
    from release_sorter import sort_releases
    # Bug: lex gives ["v1.2.9", "v1.2.10"]; expected: ["v1.2.10", "v1.2.9"]
    result = sort_releases(["v1.2.9", "v1.2.10"])
    assert result == ["v1.2.10", "v1.2.9"], (
        f"expected ['v1.2.10', 'v1.2.9'] (semver), got {result}"
    )


def test_mixed_versions_correct_order():
    from release_sorter import sort_releases
    # Bug: lex gives ["v2.0.0", "v1.9.0", "v1.10.0"]; expected v1.10.0 > v1.9.0
    result = sort_releases(["v2.0.0", "v1.9.0", "v1.10.0"])
    assert result == ["v2.0.0", "v1.10.0", "v1.9.0"], (
        f"expected ['v2.0.0', 'v1.10.0', 'v1.9.0'], got {result}"
    )
