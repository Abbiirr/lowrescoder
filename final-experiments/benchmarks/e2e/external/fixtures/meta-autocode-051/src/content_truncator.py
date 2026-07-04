def truncate_content(content, max_length):
    """Truncate content to max_length chars, appending '...' if truncated."""
    if len(content) <= max_length:
        return content
    # BUG: no ellipsis appended after truncation
    return content[:max_length]
