def deduplicate(items):
    """Return items with duplicates removed, preserving first occurrence order."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            result.append(item)
            # BUG: missing seen.add(item) — set never tracks what was appended
    return result
