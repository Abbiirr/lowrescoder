def is_timeout_error(error):
    """Return True if the error is a request timeout."""
    # BUG: checks 'type' key instead of 'code'
    return error.get('type') == 'TIMEOUT'
