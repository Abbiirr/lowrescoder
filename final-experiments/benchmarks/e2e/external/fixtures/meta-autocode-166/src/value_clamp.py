def clamp(value, min_val, max_val):
    """Return value clamped to [min_val, max_val]."""
    # BUG: bounds swapped — returns max_val when below min, min_val when above max
    if value < min_val:
        return max_val
    if value > max_val:
        return min_val
    return value
