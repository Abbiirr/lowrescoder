def has_permission(user, required_permissions):
    """Return True only if user has ALL required permissions."""
    user_perms = set(user.get('permissions', []))
    # BUG: any() instead of all() — passes if user has ANY required permission
    return any(perm in user_perms for perm in required_permissions)
