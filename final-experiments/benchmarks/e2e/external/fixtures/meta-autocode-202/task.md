# TASK-202: Fix URL Builder Double Slash on Trailing-Slash Base (axios pattern)

## Source
Inspired by axios/axios URL construction. Simple string concatenation creates
double slashes (`//`) when the base URL has a trailing slash and the path has
a leading slash.

## Goal
Fix `src/url_builder.py` so `build_url()` produces a single slash regardless
of trailing/leading slashes on its inputs.

## The bug
```python
# BUG: double slash when base ends with '/' and path starts with '/'
return base + path

# Fix:
return base.rstrip('/') + '/' + path.lstrip('/')
```

## Failing tests (3/7 fail initially)
```
test_trailing_slash_base ← FAILS ('http://api.com/' + '/users' → '//')
test_versioned_trailing  ← FAILS (same double-slash issue)
test_cdn_trailing        ← FAILS (same)
```
