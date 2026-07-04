def update_watch_count(repo, user_id, watching):
    """Set watch status; return updated watch count."""
    watchers = repo.setdefault('watchers', set())
    if watching:
        watchers.add(user_id)
    else:
        watchers.discard(user_id)
    # BUG: returns len of watchers set instead of updating repo['watch_count']
    return len(watchers)
