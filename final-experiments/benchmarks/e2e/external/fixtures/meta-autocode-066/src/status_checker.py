def is_status_ok(status_code):
    """Return True if HTTP status code indicates success (2xx range)."""
    # BUG: only accepts exactly 200 — misses 201, 202, 204, etc.
    return status_code == 200
