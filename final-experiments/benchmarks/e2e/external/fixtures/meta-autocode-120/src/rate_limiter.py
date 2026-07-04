import time

_buckets = {}

def is_allowed(client_id, max_requests, window_seconds, _now=None):
    """Return True if client is within rate limit, False if exceeded."""
    now = _now if _now is not None else time.time()
    if client_id not in _buckets:
        _buckets[client_id] = {'count': 0, 'window_start': now}
    bucket = _buckets[client_id]
    if now - bucket['window_start'] >= window_seconds:
        bucket['count'] = 0
        bucket['window_start'] = now
    bucket['count'] += 1
    # BUG: < instead of <= blocks the last allowed request
    return bucket['count'] < max_requests
