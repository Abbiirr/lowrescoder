def have_overlapping_keys(d1, d2):
    """Return True if d1 and d2 share at least one key."""
    # BUG: checks equality of key sets — only True when both have identical keys
    return set(d1.keys()) == set(d2.keys())
