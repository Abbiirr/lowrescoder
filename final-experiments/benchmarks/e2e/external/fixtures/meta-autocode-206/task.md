# TASK-206: Fix Content Truncation Exceeds max_len (memos pattern)

## Source
Inspired by usememos/memos content preview. Appending `'...'` without
reducing the slice by 3 makes the result `max_len + 3` characters long.

## Goal
Fix `src/content_truncator.py` so `truncate_content()` keeps total length
exactly `max_len`.

## The bug
```python
# BUG: result is max_len + 3 chars
return content[:max_len] + '...'

# Fix:
return content[:max_len - 3] + '...'
```

## Failing tests (3/7 fail initially)
```
test_long_content   ← FAILS (result 'hello wo...' = 11 chars > 8)
test_medium_content ← FAILS (result 'abcde...' = 8 chars > 5)
test_max_len_10     ← FAILS (result 'long conte...' = 13 chars > 10)
```
