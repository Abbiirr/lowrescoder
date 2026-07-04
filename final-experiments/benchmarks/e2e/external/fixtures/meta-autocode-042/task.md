# TASK-042: Fix URL Builder Double Slash (axios/axios pattern)

## Source
Inspired by axios/axios baseURL + path concatenation. When the path starts
with `/` and the base URL is stripped of its trailing slash, combining them
naive-ly produces a double slash in the URL. The bug strips the trailing slash
from the base but doesn't strip the leading slash from the path.

## Goal
Fix `src/url_builder.py` so `build_url()` produces a clean URL regardless of
whether `path` starts with `/`.

## The bug
```python
# BUG: doesn't strip leading slash from path
return base_url.rstrip('/') + '/' + path

# Fix: strip both sides
return base_url.rstrip('/') + '/' + path.lstrip('/')
```

## Failing tests (3/7 fail initially)
```
test_path_with_leading_slash      ← FAILS ('//users' in result)
test_both_trailing_and_leading_slash ← FAILS ('//v1/items' in result)
test_deep_path_with_leading_slash ← FAILS ('//api/v2/search' in result)
```
