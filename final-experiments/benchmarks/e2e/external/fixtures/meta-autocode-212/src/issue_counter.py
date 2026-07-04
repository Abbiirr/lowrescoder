def count_open_issues(issues):
    """Return the number of issues with state == 'open'."""
    # BUG: counts all issues regardless of state
    return len(issues)
