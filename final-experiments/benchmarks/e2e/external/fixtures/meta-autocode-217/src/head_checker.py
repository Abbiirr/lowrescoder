def is_detached_head(head_info):
    """Return True if HEAD is in a detached state."""
    # BUG: wrong key 'detached' instead of 'is_detached'
    return bool(head_info.get('detached'))
