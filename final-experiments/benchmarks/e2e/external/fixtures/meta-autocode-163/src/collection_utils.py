def all_unique(items):
    """Return True if all elements in items are unique, False otherwise."""
    seen = set()
    for item in items:
        if item in seen:
            return False
        seen.add(item)
    # BUG: missing 'return True' — returns None for all-unique lists
