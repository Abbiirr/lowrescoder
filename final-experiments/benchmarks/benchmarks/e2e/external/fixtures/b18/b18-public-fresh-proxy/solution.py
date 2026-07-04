"""Prototype held-out proxy solution."""

from __future__ import annotations


def latest_stable_version(tags: list[str]) -> str | None:
    """Return the latest stable version tag.

    Broken on purpose: this uses lexicographic ordering and does not filter
    prereleases correctly.
    """
    cleaned = [tag.lstrip("v") for tag in tags if "." in tag and "-" not in tag]
    if not cleaned:
        return None
    return sorted(cleaned)[-1]
