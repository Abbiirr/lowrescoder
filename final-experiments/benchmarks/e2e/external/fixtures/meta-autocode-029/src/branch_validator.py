def is_valid_branch_name(name):
    """Return True if name is a valid git branch name."""
    if not name:
        return False
    invalid_chars = [' ', '~', '^', ':', '?', '*', '[', '\\']
    for c in invalid_chars:
        if c in name:
            return False
    # BUG: rejects any dot — only '..' (double-dot) is forbidden in git refs
    if '.' in name:
        return False
    return True
