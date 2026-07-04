def is_absolute_url(url):
    """Return True if url has an http or https scheme."""
    # BUG: only checks for 'http://' — misses 'https://' URLs
    return url.startswith('http://')
