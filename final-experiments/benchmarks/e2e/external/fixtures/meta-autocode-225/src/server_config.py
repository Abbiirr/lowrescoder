def get_port(config, default=3000):
    """Return configured server port, or default if not set."""
    # BUG: wrong key 'server_port' instead of 'port'
    return config.get('server_port', default)
