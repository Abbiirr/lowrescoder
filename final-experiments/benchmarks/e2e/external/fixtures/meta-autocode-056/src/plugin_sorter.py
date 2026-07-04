def sort_plugins(plugins):
    """Sort plugins by enforce: 'pre' first, then normal (no enforce), then 'post'."""
    # BUG: returns plugins in original registration order, ignoring enforce
    return plugins
