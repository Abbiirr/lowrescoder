def is_valid_repo_name(name):
    """Return True if name has no special chars (spaces, dots, slashes)."""
    # BUG: checks space and dot but misses slash
    return ' ' not in name and '.' not in name
