def get_nested(config, *keys, default=None):
    """Safely get a deeply nested config value."""
    current = config
    for key in keys:
        if not isinstance(current, dict):
            return default
        # BUG: .get() conflates missing key with None value;
        # use 'key not in current' check instead
        current = current.get(key)
        if current is None:
            return default
    return current
