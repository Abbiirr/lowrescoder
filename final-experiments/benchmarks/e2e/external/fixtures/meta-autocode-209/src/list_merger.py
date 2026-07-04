def merge_unique(list1, list2):
    """Return unique items from both lists combined, preserving first-seen order."""
    # BUG: no deduplication — returns concatenation with duplicates
    return list1 + list2
