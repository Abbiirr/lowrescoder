def parse_path_param(value, param_type):
    """Coerce a URL path parameter string to the declared type."""
    if param_type == 'int':
        # BUG: str.isdigit() returns False for negative numbers — '-1'.isdigit() is False
        if not value.isdigit():
            raise ValueError(f"Invalid integer path parameter: {value!r}")
        return int(value)
    return value
