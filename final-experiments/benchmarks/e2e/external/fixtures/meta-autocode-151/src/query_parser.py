def parse_query_string(query):
    """Parse a URL query string (key=value&key2=value2) into a dict."""
    result = {}
    for part in query.split('&'):
        if not part:
            continue
        # BUG: split('=') without maxsplit — crashes when value contains '='
        k, v = part.split('=')
        result[k] = v
    return result
