def merge_request_headers(base_headers, request_headers):
    """Merge request-level headers over base (instance) headers."""
    result = base_headers.copy()
    # BUG: updates base with request headers instead of creating merged copy
    result.update(request_headers)
    # BUG: also sets Content-Type unconditionally, overwriting caller's value
    result['Content-Type'] = 'application/json'
    return result
