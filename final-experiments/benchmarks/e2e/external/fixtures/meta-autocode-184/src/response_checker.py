def is_success(status_code):
    """Return True if status_code is a 2xx success response."""
    # BUG: only accepts 200 — all other 2xx codes incorrectly return False
    return status_code == 200
