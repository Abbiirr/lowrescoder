def count_public_memos(memos):
    """Return the count of memos with visibility='PUBLIC'."""
    # BUG: counts all memos regardless of visibility field
    return len(memos)
