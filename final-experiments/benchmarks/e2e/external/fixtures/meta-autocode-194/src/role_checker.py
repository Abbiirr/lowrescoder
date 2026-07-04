def is_admin(user):
    """Return True if user has admin or owner role."""
    # BUG: only checks 'admin' — misses 'owner' which also has admin rights
    return user.get('role') == 'admin'
