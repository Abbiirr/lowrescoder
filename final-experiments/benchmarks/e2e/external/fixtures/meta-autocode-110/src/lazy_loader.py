_cache = {}

def get_or_load(key, loader_fn):
    """Return cached value, or call loader_fn() and cache it."""
    # BUG: checks 'key in _cache' but then calls loader even when present
    if key not in _cache:
        _cache[key] = loader_fn()
    result = loader_fn()  # BUG: always calls loader_fn
    return result
