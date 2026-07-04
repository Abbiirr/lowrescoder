def encode_params(params):
    """Encode a dict of params to a URL query string.
    List values become repeated keys: {'ids': [1,2]} -> 'ids=1&ids=2'
    """
    parts = []
    for key, value in params.items():
        if isinstance(value, list):
            # BUG: joins list values with comma instead of repeating the key
            parts.append(f"{key}={','.join(str(v) for v in value)}")
        else:
            parts.append(f"{key}={value}")
    return '&'.join(parts)
