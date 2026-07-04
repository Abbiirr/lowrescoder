def should_retry(status_code, max_retries, current_attempt):
    """Return True if the request should be retried."""
    if current_attempt >= max_retries:
        return False
    # BUG: only retries on exactly 500 — 502/503/504 should also trigger retry
    return status_code == 500
