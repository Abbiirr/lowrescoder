# TASK-211: Fix get_query_string Crashes on URLs Without Query String (axios pattern)

## Source
Inspired by axios/axios URL parsing. Naive `split('?')[1]` crashes with
IndexError when no query string is present.

## Goal
Fix `src/query_parser.py` so `get_query_string()` returns `''` for URLs
that have no `?`.

## The bug
```python
# BUG: IndexError when no '?'
return url.split('?')[1]

# Fix:
parts = url.split('?', 1)
return parts[1] if len(parts) > 1 else ''
```

## Failing tests (3/7 fail initially)
```
test_no_query_bare   ← FAILS (IndexError on 'http://example.com')
test_no_query_path   ← FAILS (IndexError on 'http://example.com/path')
test_no_query_root   ← FAILS (IndexError on '/')
```
