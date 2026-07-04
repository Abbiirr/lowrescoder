def rotate_right(items):
    """Rotate list one position to the right (last element moves to front)."""
    if len(items) <= 1:
        return items[:]
    # BUG: rotates left (first element to back) instead of right
    return items[1:] + items[:1]
