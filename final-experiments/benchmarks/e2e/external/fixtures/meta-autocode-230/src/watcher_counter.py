def count_watchers(repo):
    """Return the repository watcher count."""
    # BUG: reads 'stargazers_count' instead of 'watchers_count'
    return repo.get('stargazers_count', 0)
