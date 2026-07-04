def should_retry(status_code, attempt, max_attempts):
    """Return True if the request should be retried based on status code."""
    if attempt >= max_attempts:
        return False
    # BUG: retries on 200 (success) instead of 5xx (server errors)
    return status_code == 200
