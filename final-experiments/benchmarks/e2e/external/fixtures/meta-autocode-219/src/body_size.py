def is_body_too_large(content, max_size):
    """Return True only if content length strictly exceeds max_size."""
    # BUG: >= flags exact-limit bodies as too large
    return len(content) >= max_size
