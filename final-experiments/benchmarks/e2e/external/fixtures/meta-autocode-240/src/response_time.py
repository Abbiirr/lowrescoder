def format_response_time(ms):
    """Return response time as 'Xms' for under 1000ms, 'X.XXs' otherwise."""
    if ms < 1000:
        return f'{ms}ms'
    # BUG: divides by 100 instead of 1000 — off by factor of 10
    return f'{ms / 100:.2f}s'
