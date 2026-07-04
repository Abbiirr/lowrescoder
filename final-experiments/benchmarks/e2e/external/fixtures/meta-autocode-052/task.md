# TASK-052: Fix Response Model Exclude None (fastapi/fastapi pattern)

## Source
Inspired by FastAPI's `response_model_exclude_none` feature which strips None
fields from serialized responses. The bug ignores the `exclude_none` flag and
always returns all fields including None values.

## Goal
Fix `src/response_serializer.py` so `serialize_response(data, exclude_none=True)`
omits keys whose value is `None`.

## The bug
```python
# BUG: ignores exclude_none
return {k: v for k, v in data.items()}

# Fix: honour the flag
if exclude_none:
    return {k: v for k, v in data.items() if v is not None}
return {k: v for k, v in data.items()}
```

## Failing tests (3/7 fail initially)
```
test_exclude_single_none    ← FAILS ({'a': None, 'b': 2} with exclude_none=True returns None)
test_exclude_all_none       ← FAILS ({'a': None, 'b': None} returns non-empty dict)
test_exclude_none_mixed_types ← FAILS (0 and False stripped alongside None)
```
