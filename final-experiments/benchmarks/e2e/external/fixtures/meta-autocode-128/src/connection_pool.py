_pool = []

def add_connection(conn):
    _pool.append(conn)

def get_connection():
    """Return a healthy connection from the pool, or None if none available."""
    for i, conn in enumerate(_pool):
        # BUG: returns connection without checking health
        conn_obj = _pool.pop(i)
        return conn_obj
    return None

def clear_pool():
    _pool.clear()
