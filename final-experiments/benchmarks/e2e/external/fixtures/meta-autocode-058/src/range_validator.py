def validate_int_range(value, ge=None, le=None):
    """Validate that an integer satisfies optional ge (>=) and le (<=) bounds."""
    # BUG: no range check — returns value unchanged regardless of bounds
    return value
