def is_safe_path(path):
    """Return True if path contains no directory traversal (no '..' component)."""
    # BUG: substring check — '..' in 'file..txt' incorrectly blocks valid filenames
    if '..' in path:
        return False
    return True
