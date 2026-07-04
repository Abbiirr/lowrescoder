def get_default_branch(repo):
    """Return the repository's default branch name."""
    # BUG: reads 'default' instead of 'default_branch'
    return repo.get('default', 'main')
