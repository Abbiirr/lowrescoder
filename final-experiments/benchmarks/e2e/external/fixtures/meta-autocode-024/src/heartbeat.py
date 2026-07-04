"""Uptime-kuma heartbeat status — inspired by louislam/uptime-kuma HTTP monitor."""


def compute_status(response_code, expected_codes=None):
    """Return True if response_code indicates 'up'.

    If expected_codes is provided, only those exact codes count as up.
    Otherwise, any 2xx response should be up.
    """
    if expected_codes is not None:
        return response_code in expected_codes
    # BUG: only 200 is checked; any 2xx should be considered up
    return response_code == 200
