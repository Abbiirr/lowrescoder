# Semantic version comparison — has a bug.
# This file exists to be fixed by the agent.


def parse_version(version_str: str) -> tuple:
    """Parse 'v1.2.3' or '1.2.3' into (1, 2, 3)."""
    return tuple(int(p) for p in version_str.lstrip("v").split("."))


def is_newer(version_a: str, version_b: str) -> bool:
    """Return True if version_a is strictly newer than version_b.

    Bug: compares raw strings instead of parsed tuples.
    String comparison is lexicographic, so "1.10.0" < "1.9.0" because
    the character '1' < '9', making minor-version jumps report wrong results.
    """
    return version_a > version_b  # BUG: string comparison


def latest(versions: list) -> str:
    """Return the latest version from a list of version strings."""
    return max(versions)  # BUG: max() on strings uses lexicographic order
