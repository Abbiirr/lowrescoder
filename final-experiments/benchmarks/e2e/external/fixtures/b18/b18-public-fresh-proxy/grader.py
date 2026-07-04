"""Deterministic grader for the B18 prototype fixture."""

from __future__ import annotations

from solution import latest_stable_version


def _assert_equal(actual, expected, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def main() -> None:
    _assert_equal(
        latest_stable_version(["v1.2.0", "1.10.0", "v1.9.9"]),
        "1.10.0",
        "highest stable version",
    )
    _assert_equal(
        latest_stable_version(["v2.0.0-rc1", "v1.9.0"]),
        "1.9.0",
        "ignore prereleases",
    )
    _assert_equal(
        latest_stable_version(["nightly", "bad-tag"]),
        None,
        "ignore malformed tags",
    )
    _assert_equal(
        latest_stable_version(["v1.0.0", "1.0.1", "v1.0.1-beta", "v1.0.10"]),
        "1.0.10",
        "numeric comparison",
    )
    print("PASS")


if __name__ == "__main__":
    main()
