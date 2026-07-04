def validate_config(config, required_keys):
    """Return list of missing required keys that have no value (None or missing)."""
    missing = []
    for key in required_keys:
        value = config.get(key)
        # BUG: treats 0, False, '' as missing (falsy check instead of None check)
        if not value:
            missing.append(key)
    return missing
