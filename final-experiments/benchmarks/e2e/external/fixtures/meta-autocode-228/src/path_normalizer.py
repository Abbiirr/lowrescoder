def normalize_path(path):
    """Ensure path starts with exactly one leading '/'."""
    # BUG: always prepends '/' — creates double-slash for paths already starting with '/'
    return '/' + path
