# TASK-165: Fix Cookie Header Separator (axios pattern)

## Source
Inspired by axios/axios cookie handling. HTTP Cookie headers must use `'; '`
to separate pairs, but the bug uses `','` (comma), which is invalid per RFC
6265.

## Goal
Fix `src/cookie_builder.py` so `build_cookie_header()` uses `'; '` as the
separator.

## The bug
```python
# BUG: comma separator — invalid Cookie header
return ','.join(f'{k}={v}' for k, v in cookies.items())

# Fix:
return '; '.join(f'{k}={v}' for k, v in cookies.items())
```

## Failing tests (3/7 fail initially)
```
test_two_cookies      ← FAILS ('a=1,b=2' instead of 'a=1; b=2')
test_three_cookies    ← FAILS (comma-separated instead of '; ')
test_two_real_cookies ← FAILS (comma-separated)
```
