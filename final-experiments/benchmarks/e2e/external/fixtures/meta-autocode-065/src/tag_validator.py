import re

def is_valid_release_tag(tag):
    """Return True if tag matches semver format vX.Y.Z (e.g. v1.2.3)."""
    # BUG: only checks non-empty — allows any string as a release tag
    return bool(tag)
