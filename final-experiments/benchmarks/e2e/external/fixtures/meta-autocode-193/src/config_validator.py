def has_valid_timeout(config):
    """Return True if config has a positive timeout value."""
    # BUG: only checks key existence — accepts 0 and negative values
    return 'timeout' in config
