def is_session_expired(created_at, current_time, ttl_minutes=30):
    """Return True if session has expired."""
    # BUG: treats ttl_minutes as seconds
    return (current_time - created_at) > ttl_minutes
