def abbreviate_branch(name, max_len=20):
    """Return name truncated with '...' if it exceeds max_len, else unchanged."""
    if len(name) <= max_len:
        return name
    # BUG: truncates to max_len chars without appending '...'
    return name[:max_len]
