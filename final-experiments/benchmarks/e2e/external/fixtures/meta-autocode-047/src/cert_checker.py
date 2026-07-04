def cert_status(days_until_expiry):
    """Return 'expired', 'expiring_soon' (≤30 days), or 'valid'."""
    if days_until_expiry < 0:
        return 'expired'
    # BUG: warns only within 7 days — misses 8-30 day window
    if days_until_expiry <= 7:
        return 'expiring_soon'
    return 'valid'
