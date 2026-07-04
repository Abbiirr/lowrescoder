def resolve_request_timeout(instance_timeout, request_timeout):
    """Return effective timeout: request_timeout overrides instance_timeout when set."""
    # BUG: ignores request_timeout — always returns the instance-level default
    return instance_timeout
