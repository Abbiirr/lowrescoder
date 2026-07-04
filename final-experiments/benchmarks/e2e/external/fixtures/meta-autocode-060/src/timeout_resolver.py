DEFAULT_TIMEOUT = 30

def resolve_timeout(timeout):
    """Return timeout in seconds; fall back to DEFAULT_TIMEOUT when timeout <= 0."""
    # BUG: returns raw value — negative/zero timeouts not replaced with default
    return timeout
