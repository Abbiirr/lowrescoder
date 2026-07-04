def get_stash_count(stash_info):
    """Return the number of stash entries."""
    # BUG: reads 'count' instead of 'entries'
    return stash_info.get('count', 0)
