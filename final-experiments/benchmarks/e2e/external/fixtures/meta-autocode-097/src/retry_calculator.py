def get_retry_delay(attempt, base_delay=1.0, max_delay=60.0):
    """Exponential backoff: base_delay * 2^attempt, capped at max_delay."""
    # BUG: uses addition instead of multiplication for exponential
    delay = base_delay + (2 ** attempt)
    return min(delay, max_delay)
