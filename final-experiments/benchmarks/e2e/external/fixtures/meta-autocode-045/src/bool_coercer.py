def coerce_to_bool(value):
    """Coerce a value to bool, handling string representations."""
    if isinstance(value, bool):
        return value
    # BUG: bool("false") is True — non-empty strings are always truthy in Python
    return bool(value)
