def build_cookie_header(cookies):
    """Build HTTP Cookie header string (key=value pairs separated by '; ')."""
    # BUG: uses ',' separator instead of '; '
    return ','.join(f'{k}={v}' for k, v in cookies.items())
