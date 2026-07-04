# TASK-091: Fix URL Path Join Missing Slash (axios/axios pattern)

## Source
Inspired by axios/axios URL path resolution. When the path doesn't start with
`/`, the joiner must insert one between base and path.

## Goal
Fix `src/path_joiner.py` so `join_url_path()` always produces exactly one
slash between base and path.

## The bug
```python
# BUG: no slash insertion for paths without leading /
return base.rstrip('/') + path

# Fix:
return base.rstrip('/') + '/' + path.lstrip('/')
```

## Failing tests (3/7 fail initially)
```
test_no_leading_slash_path          ← FAILS ('http://example.comapi' != '.../api')
test_no_leading_slash_with_trailing ← FAILS ('http://example.comusers' != '.../users')
test_deep_path_no_leading_slash     ← FAILS ('http://hostv1/items' != '.../v1/items')
```
