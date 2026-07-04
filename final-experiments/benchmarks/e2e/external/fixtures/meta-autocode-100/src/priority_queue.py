def get_highest_priority(items):
    """Return item with highest priority value. Returns None if empty."""
    if not items:
        return None
    # BUG: returns minimum priority instead of maximum
    return min(items, key=lambda x: x.get('priority', 0))
