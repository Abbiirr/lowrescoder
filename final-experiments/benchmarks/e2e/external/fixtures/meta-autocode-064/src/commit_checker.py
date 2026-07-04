def check_commit_message(message):
    """Return list of warnings about commit message style."""
    warnings = []
    first_line = message.split('\n')[0]
    # BUG: warns only beyond 72 chars; conventional subject limit is 50
    if len(first_line) > 72:
        warnings.append('First line too long (> 50 chars recommended)')
    return warnings
