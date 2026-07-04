_ALLOWED_METHODS = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'}

def is_valid_method(method):
    """Return True if method is a valid HTTP method (case-insensitive)."""
    # BUG: case-sensitive — 'get' not in {'GET', ...}
    return method in _ALLOWED_METHODS
