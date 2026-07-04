def is_prerelease(version):
    """Return True if version is a pre-release (contains '-' per semver)."""
    # BUG: checks for '+' (build metadata) instead of '-' (pre-release marker)
    return '+' in version
