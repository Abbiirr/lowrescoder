def short_hash(commit_hash):
    """Return the short (7-character) version of a commit hash."""
    # BUG: returns 6 characters instead of 7
    return commit_hash[:6]
