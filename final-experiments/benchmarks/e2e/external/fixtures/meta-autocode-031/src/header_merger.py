def merge_request_headers(defaults, config_headers):
    """Merge default headers with per-request headers (config wins on conflict)."""
    if config_headers is None:
        return defaults.copy()
    # BUG: returns config_headers only — discards defaults entirely
    return config_headers
