def find_mode(items):
    """Return the most frequently occurring item (mode) in the list."""
    if not items:
        return None
    counts = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    # BUG: returns item with minimum count instead of maximum
    return min(counts, key=lambda k: counts[k])
