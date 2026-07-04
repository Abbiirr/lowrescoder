def count_changes(old_lines, new_lines):
    """Count added and removed lines between old and new content."""
    old_set = set(old_lines)
    new_set = set(new_lines)
    # BUG: uses set operations — counts lines unique to each side,
    # but ignores that a line appearing in both could be 'unchanged'
    # Actually the real bug: counts len(new_lines) as additions instead of set diff
    added = len(new_lines)   # BUG: should be len(new_set - old_set)
    removed = len(old_set - new_set)
    return {'added': added, 'removed': removed}
