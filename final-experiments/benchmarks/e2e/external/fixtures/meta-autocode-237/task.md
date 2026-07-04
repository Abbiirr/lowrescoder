# TASK-237: Fix parse_query_int Crashes on None Input (fastapi pattern)

## Source
Inspired by fastapi/fastapi query parameter parsing. Calling int(None) raises
TypeError when the query parameter is absent.

## Goal
Fix `src/query_param.py` so `parse_query_int()` returns `default` when
`value` is None.

## The bug
```python
# BUG: int(None) raises TypeError
return int(value)

# Fix:
return int(value) if value is not None else default
```

## Failing tests (3/7 fail initially)
```
test_none_default_zero ← FAILS (None → bug:TypeError, correct:0)
test_none_default_ten  ← FAILS (None, 10 → bug:TypeError, correct:10)
test_none_default_99   ← FAILS (None, 99 → bug:TypeError, correct:99)
```
