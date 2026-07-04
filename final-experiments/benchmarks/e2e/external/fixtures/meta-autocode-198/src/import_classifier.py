def is_bare_import(path):
    """Return True if path is a bare module specifier (not a relative path)."""
    # BUG: only checks for './' — misses '../' relative paths
    return not path.startswith('./')
