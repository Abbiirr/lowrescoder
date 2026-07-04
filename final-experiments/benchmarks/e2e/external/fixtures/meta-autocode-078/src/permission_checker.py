def user_has_permission(user_level, required_level):
    """Return True if user's permission level meets or exceeds required_level."""
    # BUG: equality check — higher level doesn't grant lower-level permission
    return user_level == required_level
