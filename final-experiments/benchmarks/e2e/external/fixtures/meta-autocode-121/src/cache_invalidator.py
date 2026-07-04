def invalidate_keys(cache, tags, tag_index):
    """Remove all cache entries that have any of the given tags."""
    keys_to_remove = []
    for tag in tags:
        # BUG: reassigns instead of extending — only last tag's keys are removed
        keys_to_remove = tag_index.get(tag, [])
    for key in keys_to_remove:
        cache.pop(key, None)
    return cache
