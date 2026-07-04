def build_api_response(data, status_code=200, headers=None):
    """Build standard API response dict."""
    response = {
        'status': status_code,
        'data': data,
        'headers': headers or {},
    }
    # BUG: 'success' field based on status == 200 only, misses 201, 204 etc.
    response['success'] = (status_code == 200)
    return response
