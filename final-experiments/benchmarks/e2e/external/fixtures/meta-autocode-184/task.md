# TASK-184: Fix Success Check Only Accepts 200 (axios pattern)

## Source
Inspired by axios/axios response validation. Checking `status_code == 200`
rejects all other valid 2xx responses (201, 204, 206, etc.).

## Goal
Fix `src/response_checker.py` so `is_success()` accepts any 2xx status code.

## The bug
```python
# BUG: only 200 is accepted
return status_code == 200

# Fix:
return 200 <= status_code < 300
```

## Failing tests (3/7 fail initially)
```
test_201_created   ← FAILS (201 is success — bug returns False)
test_204_no_content ← FAILS (204 is success — bug returns False)
test_206_partial   ← FAILS (206 is success — bug returns False)
```
