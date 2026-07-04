def fork_repository(repo):
    """Record a fork event by incrementing the parent repository's fork count."""
    # BUG: assignment without increment — fork_count never changes
    repo['fork_count'] = repo['fork_count']
    return repo
