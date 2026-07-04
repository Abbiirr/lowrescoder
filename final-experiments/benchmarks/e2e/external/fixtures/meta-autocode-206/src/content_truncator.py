def truncate_content(content, max_len):
    """Return content truncated to max_len chars, with '...' if truncated."""
    if len(content) <= max_len:
        return content
    # BUG: appends '...' without accounting for its 3-char width — result exceeds max_len
    return content[:max_len] + '...'
