# TASK-134: Fix URL Builder HTML Entity Encoding (axios/axios pattern)

## Source
Inspired by axios URL parameter serialization. Uses `&amp;` (HTML entity)
instead of `&` to join query parameters, producing invalid URLs.

## Goal
Fix `src/url_builder.py` so `build_query_string()` joins params with `&`.

## The bug
```python
# BUG: HTML entity instead of URL separator
return '?' + '&amp;'.join(parts)

# Fix:
return '?' + '&'.join(parts)
```

## Failing tests (3/7 fail initially)
```
test_two_params_separator ← FAILS ('&amp;' found in result)
test_correct_ampersand    ← FAILS ('&' absent, '&amp;' present)
test_three_params         ← FAILS (0 '&' and 2 '&amp;' found)
```
