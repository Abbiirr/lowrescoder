def get_query_string(url):
    """Return the query string portion of a URL, or '' if none."""
    # BUG: IndexError when URL has no '?'
    return url.split('?')[1]
