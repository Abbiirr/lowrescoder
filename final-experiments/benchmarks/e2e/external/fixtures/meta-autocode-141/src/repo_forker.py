def fork_repository(repo, user_id):
    """Fork a repository: create a copy and increment the fork count."""
    fork = {
        'name': repo['name'],
        'owner': user_id,
        'parent_id': repo['id'],
        'stars': 0,
        'forks': 0,
    }
    # BUG: decrements fork_count instead of incrementing
    repo['fork_count'] = repo.get('fork_count', 0) - 1
    return fork
