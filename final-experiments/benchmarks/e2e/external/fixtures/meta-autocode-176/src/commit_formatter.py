def format_commit(prefix, message):
    """Return a conventional commit string: 'prefix: message'."""
    # BUG: message not stripped — leading/trailing whitespace leaks into output
    return f"{prefix}: {message}"
