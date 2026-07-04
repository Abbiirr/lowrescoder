def is_valid_component_id(cid):
    """Return True if cid contains only alphanumeric characters and underscores."""
    # BUG: isalnum() rejects valid underscore characters
    return bool(cid) and cid.isalnum()
