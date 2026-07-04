def can_fork(user, repo):
    """Return True if user can fork the repository (requires at least read access)."""
    # BUG: requires write or admin — fork only needs read permission
    return user.get('permission') in ('write', 'admin')
