# TASK-183: Fix Content-Type Parser Trailing Whitespace (fastapi pattern)

## Source
Inspired by fastapi/fastapi request content-type parsing. Using `lstrip()`
instead of `strip()` leaves trailing spaces when a space precedes the `;`
separator (e.g. 'text/html ;charset=utf-8').

## Goal
Fix `src/content_type_parser.py` so `parse_content_type()` removes both
leading and trailing whitespace from the base type.

## The bug
```python
# BUG: lstrip only — trailing space leaks
return header.split(';')[0].lstrip()

# Fix:
return header.split(';')[0].strip()
```

## Failing tests (3/7 fail initially)
```
test_trailing_space_no_params    ← FAILS ('application/json ' → has trailing space)
test_space_before_semicolon      ← FAILS ('text/html ;...' → split[0]='text/html ')
test_multipart_space_before_semicolon ← FAILS (same trailing-space issue)
```
