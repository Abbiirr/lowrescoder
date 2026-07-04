def toggle_star(repo, user_id):
    """Star or unstar a repo; return updated star count."""
    starred_by = repo.setdefault('starred_by', set())
    if user_id in starred_by:
        starred_by.discard(user_id)
        # BUG: increments instead of decrements on unstar
        repo['stars'] = repo.get('stars', 0) + 1
    else:
        starred_by.add(user_id)
        repo['stars'] = repo.get('stars', 0) + 1
    return repo['stars']
