def is_dev_mode(config):
    """Return True if the build mode is 'development'."""
    # BUG: checks 'env' key instead of 'mode'
    return config.get('env') == 'development'
