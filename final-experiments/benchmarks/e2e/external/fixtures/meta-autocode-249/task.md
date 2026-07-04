# TASK-249: Fix get_monitor_url() Wrong Key 'endpoint' vs 'url' (uptime-kuma pattern)

## Source
Inspired by louislam/uptime-kuma monitor config. Monitor uses 'url', not 'endpoint'.

## Goal
Fix `src/monitor_url.py` so `get_monitor_url()` reads the correct `'url'` key.

## The bug
```python
# BUG: wrong key
return monitor.get('endpoint', default)

# Fix:
return monitor.get('url', default)
```

## Failing tests (3/7 fail initially)
```
test_https_url       ← FAILS ({'url': 'https://example.com'} → bug:'', correct:'https://example.com')
test_http_url_with_type ← FAILS ({'url': 'http://api.local'} → bug:'', correct:'http://api.local')
test_another_https   ← FAILS ({'url': 'https://test.org'} → bug:'', correct:'https://test.org')
```
