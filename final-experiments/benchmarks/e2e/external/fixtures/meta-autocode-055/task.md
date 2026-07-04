# TASK-055: Fix Case-Insensitive HTTP Header Lookup (axios/axios pattern)

## Source
Inspired by axios/axios header handling. HTTP headers are case-insensitive
per RFC 7230. The bug uses a direct dict lookup which is case-sensitive,
causing `Content-Type` and `content-type` to be treated as different headers.

## Goal
Fix `src/header_checker.py` so `has_header()` performs a case-insensitive
comparison.

## The bug
```python
# BUG: case-sensitive — 'content-type' != 'Content-Type'
return name in headers

# Fix: compare lowercased keys
return name.lower() in {k.lower() for k in headers}
```

## Failing tests (3/7 fail initially)
```
test_lowercase_lookup_on_title_case       ← FAILS ('content-type' not found in {'Content-Type': ...})
test_uppercase_stored_lowercase_lookup    ← FAILS ('authorization' not found in {'AUTHORIZATION': ...})
test_title_case_lookup_on_lowercase_stored ← FAILS ('Content-Type' not found in {'content-type': ...})
```
