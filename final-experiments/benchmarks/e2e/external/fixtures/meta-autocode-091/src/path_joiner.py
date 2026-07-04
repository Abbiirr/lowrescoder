def join_url_path(base, path):
    """Join base URL and path with exactly one slash separator."""
    # BUG: doesn't insert / when path lacks a leading slash
    return base.rstrip('/') + path
