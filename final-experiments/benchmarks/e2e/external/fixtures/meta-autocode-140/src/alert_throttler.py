def should_send_alert(last_sent_ts, current_ts, cooldown_minutes):
    """Return True if enough time has passed since last alert."""
    # BUG: compares timestamps in seconds against cooldown in minutes (off by 60x)
    elapsed = current_ts - last_sent_ts
    return elapsed >= cooldown_minutes
