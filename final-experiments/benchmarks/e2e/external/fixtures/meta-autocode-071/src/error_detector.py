def is_error_response(status_code):
    """Return True if the HTTP status code indicates an error (non-2xx)."""
    # BUG: only detects server errors (>= 500), misses client errors (4xx, 3xx)
    return status_code >= 500
