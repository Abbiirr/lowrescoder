def get_env_var(config, key, default=None):
    """Return config[key] or default if key is not present."""
    # BUG: ignores default argument — always returns None for missing keys
    return config.get(key)
