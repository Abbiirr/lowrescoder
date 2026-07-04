# TASK-010: Fix URL Builder urljoin Semantics (axios pattern)

## Source
Inspired by axios/axios and requests URL construction.
Python's urllib.parse.urljoin follows RFC 3986: without a trailing slash,
it replaces the last path segment rather than appending. Every real HTTP
client library papers over this. Classic harness-bench v2 stdlib-surprise.

## Goal
Fix `src/api_client.py` so `build_url()` always appends endpoint to base path.

## The bug
```python
# urljoin("http://api.com/v1", "users")   → "http://api.com/users"  ← wrong
# urljoin("http://api.com/v1/", "/users") → "http://api.com/users"  ← wrong

# Fix: normalize slashes and concatenate directly:
def build_url(base_url, endpoint):
    if endpoint.startswith(('http://', 'https://')):
        return endpoint          # absolute URL passthrough
    base = base_url.rstrip('/')
    path = endpoint.lstrip('/')
    if not path:
        return base_url
    return f"{base}/{path}"
```

## All 7 tests must pass
```
test_base_without_trailing_slash  ← FAILS (gets /users instead of /v1/users)
test_base_with_trailing_slash     ← passes
test_endpoint_with_leading_slash  ← FAILS (leading / treated as origin-absolute)
test_nested_base_no_slash         ← FAILS
test_empty_endpoint_returns_base  ← passes
test_absolute_endpoint_passthrough← passes
test_deep_path_endpoint           ← FAILS
```
