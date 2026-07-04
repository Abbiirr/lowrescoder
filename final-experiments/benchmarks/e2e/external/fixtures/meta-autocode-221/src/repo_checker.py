def is_repo_archived(repo):
    """Return True if the repository is marked as archived."""
    # BUG: wrong key 'is_archive' instead of 'archived'
    return bool(repo.get('is_archive'))
