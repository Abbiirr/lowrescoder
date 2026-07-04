def resolve_import(module_name, search_paths):
    """Find the first search path that contains the module."""
    for path in search_paths:
        # BUG: checks if path is in module_name instead of module_name in path
        if path in module_name:
            return path
    return None
