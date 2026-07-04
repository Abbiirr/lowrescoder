def update_monitor_status(monitor, is_up, current_time):
    """Update monitor status and last_check timestamp on each heartbeat."""
    if not monitor.get('is_up', True):
        # BUG: only updates last_check when monitor was previously down
        monitor['last_check'] = current_time
    monitor['is_up'] = is_up
    return monitor
