def has_header(headers, name):
    """Check if a header exists in the headers dict (case-insensitive)."""
    # BUG: case-sensitive lookup — HTTP headers must be matched case-insensitively
    return name in headers
