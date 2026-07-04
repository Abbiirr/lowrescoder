def validate_limit(limit):
    """Return True if limit is a valid page size (integer in range 1-100)."""
    # BUG: max allowed is 1000 instead of 100
    return isinstance(limit, int) and 1 <= limit <= 1000
