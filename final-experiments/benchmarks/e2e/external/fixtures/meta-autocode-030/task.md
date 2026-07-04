# TASK-030: Fix Path Parameter Negative Integer Parsing (fastapi/fastapi pattern)

## Source
Inspired by fastapi/fastapi path parameter type coercion. When a route declares
an `int` path parameter, FastAPI must parse the URL string to int — including
negative values. The bug uses `str.isdigit()` which returns False for strings
like `'-1'`, rejecting valid negative integers.

## Goal
Fix `src/path_param.py` so `parse_path_param()` correctly handles negative
integer strings.

## The bug
```python
# BUG: str.isdigit() returns False for '-1', '-42', etc.
if not value.isdigit():
    raise ValueError(f"Invalid integer path parameter: {value!r}")
return int(value)

# Fix: use try/except around int() directly
try:
    return int(value)
except ValueError:
    raise ValueError(f"Invalid integer path parameter: {value!r}")
```

## Failing tests (3/7 fail initially)
```
test_negative_int    ← FAILS ('-1' raises ValueError)
test_negative_large  ← FAILS ('-100' raises ValueError)
test_negative_id     ← FAILS ('-42' raises ValueError)
```
