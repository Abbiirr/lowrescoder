def generate_release_name(version, pre_release=False):
    """Generate release name string from version tuple (major, minor, patch)."""
    major, minor, patch = version
    # BUG: uses dash instead of dot as separator
    tag = f"v{major}-{minor}-{patch}"
    if pre_release:
        tag += "-pre"
    return tag
