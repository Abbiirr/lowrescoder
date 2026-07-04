_STATUS_MAP = {'up': 'Online', 'down': 'Offline', 'pending': 'Checking'}

def get_status_label(status):
    """Return human-readable label for a monitor status string."""
    # BUG: case-sensitive lookup — 'UP', 'DOWN', 'PENDING' return None
    return _STATUS_MAP.get(status)
