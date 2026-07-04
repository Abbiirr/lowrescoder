def get_latest_memo(memos):
    """Return the memo with the most recent updated_at timestamp, or None."""
    if not memos:
        return None
    # BUG: ascending sort — returns the OLDEST memo, not the latest
    return sorted(memos, key=lambda m: m.get('updated_at', 0))[0]
