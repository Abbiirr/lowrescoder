def build_url(base_url, path):
    """Combine base URL and path into a clean URL without double slashes."""
    # BUG: doesn't strip leading slash from path — causes '//' when path starts with '/'
    return base_url.rstrip('/') + '/' + path
