def parse_query_int(value, default=0):
    """Parse a query parameter string as integer, returning default when absent."""
    # BUG: int(None) raises TypeError — crashes when value is not provided
    return int(value)
