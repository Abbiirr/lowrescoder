# TASK-229: Fix is_absolute_url Misses https:// URLs (axios pattern)

## Source
Inspired by axios/axios URL detection. Only checking for 'http://' misses
secure 'https://' URLs, falsely flagging them as relative.

## Goal
Fix `src/url_checker.py` so `is_absolute_url()` accepts both http and https.

## The bug
```python
# BUG: only http
return url.startswith('http://')

# Fix:
return url.startswith(('http://', 'https://'))
```

## Failing tests (3/7 fail initially)
```
test_https_basic ← FAILS ('https://example.com' → bug:False, correct:True)
test_https_api   ← FAILS ('https://api.github.com/v1' → bug:False)
test_https_local ← FAILS ('https://localhost:4000' → bug:False)
```
