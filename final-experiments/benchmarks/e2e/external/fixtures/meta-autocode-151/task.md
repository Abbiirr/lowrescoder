# TASK-151: Fix Query String Parsing with '=' in Values (fastapi pattern)

## Source
Inspired by fastapi/fastapi request parsing. `split('=')` without a maxsplit
argument raises `ValueError` when a query param value contains an equals sign
(e.g., base64-encoded data or nested key=value pairs).

## Goal
Fix `src/query_parser.py` so `parse_query_string()` handles `=` signs inside
values by splitting only on the first `=`.

## The bug
```python
# BUG: crashes when value contains '='
k, v = part.split('=')

# Fix: split only on first '='
k, v = part.split('=', 1)
```

## Failing tests (3/7 fail initially)
```
test_value_with_equals      ← FAILS (ValueError: too many values to unpack)
test_base64_value           ← FAILS (ValueError on trailing '=')
test_nested_equals_in_value ← FAILS (ValueError: too many values to unpack)
```
