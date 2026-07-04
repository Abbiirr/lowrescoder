def parse_content_type(header):
    """Return the base media type from a Content-Type header value."""
    # BUG: lstrip() only removes leading whitespace — trailing space (before ';') leaks through
    return header.split(';')[0].lstrip()
