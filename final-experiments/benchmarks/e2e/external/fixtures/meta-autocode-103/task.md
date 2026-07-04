# TASK-103: Fix API Response Success Flag 2xx Range (fastapi/fastapi pattern)

## Source
Inspired by fastapi/fastapi response status handling. The `success` field
should be True for any 2xx status code, not just 200.

## Goal
Fix `src/response_builder.py` so `build_api_response()` sets `success` to
True for any status in the 200-299 range.

## The bug
```python
# BUG: only 200
response['success'] = (status_code == 200)

# Fix: full 2xx range
response['success'] = (200 <= status_code < 300)
```

## Failing tests (3/7 fail initially)
```
test_201_is_success ← FAILS (False != True)
test_204_is_success ← FAILS (False != True)
test_202_is_success ← FAILS (False != True)
```
