def is_tag_ref(ref):
    """Return True if ref is a git tag reference (starts with 'refs/tags/')."""
    # BUG: typo — 'refs/tag/' is missing the 's', never matches real tags
    return ref.startswith('refs/tag/')
