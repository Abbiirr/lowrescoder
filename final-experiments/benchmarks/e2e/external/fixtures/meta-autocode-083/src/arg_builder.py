def build_git_args(base_args, extra_args):
    """Combine base and extra args into a single command string."""
    # BUG: joins with comma instead of space
    return ','.join(base_args + extra_args)
