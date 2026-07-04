def is_rate_limited(request_count, limit, window_requests):
    """Return True if the current request should be blocked (count exceeds limit)."""
    # BUG: uses > (strict), allows exactly `limit` requests instead of blocking at limit
    return request_count > limit
