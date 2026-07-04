def has_hot_reload(config):
    """Return True if hot-module-replacement is enabled in the config dict."""
    # BUG: wrong key 'hmr' instead of 'hot'
    return bool(config.get('hmr'))
