def build_query_string(params):
    """Build a URL query string from a dict of params."""
    if not params:
        return ''
    # BUG: uses HTML entity &amp; instead of &
    parts = [f"{k}={v}" for k, v in params.items()]
    return '?' + '&amp;'.join(parts)
