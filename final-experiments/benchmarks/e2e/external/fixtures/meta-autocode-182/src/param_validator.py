def is_in_range(value, min_val, max_val):
    """Return True if value is within [min_val, max_val] inclusive."""
    # BUG: excludes max_val — uses < instead of <=
    return min_val <= value < max_val
