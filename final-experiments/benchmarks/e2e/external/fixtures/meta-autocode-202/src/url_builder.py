def build_url(base, path):
    """Return full URL by joining base URL and path, ensuring single slash."""
    # BUG: simple concatenation — trailing slash on base + leading slash on path = double slash
    return base + path
