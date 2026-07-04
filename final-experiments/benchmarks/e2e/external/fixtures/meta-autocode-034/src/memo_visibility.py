def filter_by_visibility(memos, visibility):
    """Return memos matching the given visibility level."""
    # BUG: case-sensitive comparison — 'public' != 'PUBLIC'
    return [m for m in memos if m['visibility'] == visibility]
