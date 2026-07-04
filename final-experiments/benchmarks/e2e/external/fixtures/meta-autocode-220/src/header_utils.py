def strip_auth_header(headers):
    """Return headers dict with the Authorization header removed (case-insensitive)."""
    # BUG: case-sensitive key check — misses 'authorization', 'AUTHORIZATION'
    return {k: v for k, v in headers.items() if k != 'Authorization'}
