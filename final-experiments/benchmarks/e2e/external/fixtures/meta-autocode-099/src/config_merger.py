def merge_configs(base, override):
    """Deep merge override into base; lists are replaced, not appended."""
    # BUG: no copy — result IS base, so mutations affect the original
    result = base
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            merge_configs(result[key], value)
        else:
            result[key] = value
    return result
