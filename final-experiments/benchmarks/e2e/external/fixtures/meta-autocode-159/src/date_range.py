def ranges_overlap(start1, end1, start2, end2):
    """Return True if date range [start1,end1] overlaps with [start2,end2]."""
    # BUG: checks if range1 contains range2 — misses partial overlaps
    return start1 <= start2 and end1 >= end2
