def filter_lines(lines, start, end):
    """Return lines[start..end] inclusive (1-indexed)."""
    # BUG: uses >= instead of > — single-line ranges (start==end) return empty
    if start >= end:
        return []
    return lines[start - 1:end]
