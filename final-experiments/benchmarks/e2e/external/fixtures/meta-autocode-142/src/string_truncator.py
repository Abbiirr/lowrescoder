def truncate(text, max_length, ellipsis='...'):
    """Truncate text to max_length characters, adding ellipsis if truncated."""
    if len(text) <= max_length:
        return text
    # BUG: slices to max_length but then appends ellipsis, exceeding max_length
    return text[:max_length] + ellipsis
