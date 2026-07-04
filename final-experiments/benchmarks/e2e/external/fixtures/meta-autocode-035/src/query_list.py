def parse_list_query_param(query_string, param_name):
    """Parse repeated query params: ?tag=a&tag=b → ['a', 'b']"""
    result = {}
    for part in query_string.split('&'):
        if '=' in part:
            k, v = part.split('=', 1)
            if k == param_name:
                # BUG: overwrites on each occurrence — only the last value kept
                result[param_name] = v
    return [result[param_name]] if param_name in result else []
