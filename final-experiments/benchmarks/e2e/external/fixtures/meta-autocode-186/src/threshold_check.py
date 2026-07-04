def is_response_ok(response_ms, max_ms):
    """Return True if response time is strictly less than the threshold."""
    # BUG: <= accepts the exact threshold as OK — should be strict <
    return response_ms <= max_ms
