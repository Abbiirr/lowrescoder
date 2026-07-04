def is_main_branch(branch_name):
    """Return True if branch_name is exactly 'main'."""
    # BUG: startswith('main') — matches 'mainline', 'main-feature', etc.
    return branch_name.startswith('main')
