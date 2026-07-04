def apply_interceptors(value, interceptors):
    """Apply a chain of interceptor functions to value in order."""
    result = value
    # BUG: applies interceptors in reverse order
    for interceptor in reversed(interceptors):
        result = interceptor(result)
    return result
