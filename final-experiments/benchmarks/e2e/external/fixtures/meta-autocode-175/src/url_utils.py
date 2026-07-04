def is_secure_url(url):
    """Return True if url uses the HTTPS protocol."""
    # BUG: missing '://' — accepts 'httpsfoo.com' as secure
    return url.startswith('https')
