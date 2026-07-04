def validate_numeric_input(value, min_val=None, max_val=None):
    """Validate value is within [min_val, max_val] inclusive."""
    if min_val is not None and value < min_val:
        raise ValueError(f"Value {value} is below minimum {min_val}")
    # BUG: >= rejects the max value itself — should use > (exclusive upper guard)
    if max_val is not None and value >= max_val:
        raise ValueError(f"Value {value} exceeds maximum {max_val}")
