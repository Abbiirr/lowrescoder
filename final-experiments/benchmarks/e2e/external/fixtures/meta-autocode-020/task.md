# TASK-020: Fix Response Serializer Nested None Exclusion (fastapi pattern)

## Source
Inspired by fastapi/fastapi pydantic `response_model_exclude_none`.
When serializing an API response with `exclude_none=True`, None values in
nested dicts must also be removed — the shallow dict comprehension only
strips top-level None fields.

## Goal
Fix `src/response_serializer.py` so `serialize_response()` recursively removes
None values from all levels of nesting.

## The bug
```python
# BUG: only removes top-level None fields
return {k: v for k, v in data.items() if v is not None}

# Fix: recurse into nested dicts
def _strip(d):
    return {k: _strip(v) if isinstance(v, dict) else v
            for k, v in d.items() if v is not None}
return _strip(data)
```

## Failing tests (3/7 fail initially)
```
test_nested_none_excluded       ← FAILS (nickname: None kept in nested dict)
test_deeply_nested_none_excluded ← FAILS (c: None kept in deep nesting)
test_mixed_top_and_nested_none  ← FAILS (p: None kept in nested dict)
```
