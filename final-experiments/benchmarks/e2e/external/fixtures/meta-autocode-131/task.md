# TASK-131: Fix JSON Serializer Nested None Exclusion (fastapi/fastapi pattern)

## Source
Inspired by FastAPI response model serialization. `exclude_none=True` only
strips top-level None fields, leaving nested None values intact.

## Goal
Fix `src/json_serializer.py` so `serialize_response()` recursively removes
None values from nested dicts when `exclude_none=True`.

## The bug
```python
# BUG: only strips top-level None values
cleaned = {k: v for k, v in data.items() if v is not None}

# Fix: recursively clean dicts
def _clean(obj):
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items() if v is not None}
    return obj
cleaned = _clean(data)
```

## Failing tests (3/7 fail initially)
```
test_nested_none_excluded    ← FAILS (nested None survives)
test_nested_dict_none_field  ← FAILS (nested None survives)
test_deep_nested_none        ← FAILS (deeply nested None survives)
```
