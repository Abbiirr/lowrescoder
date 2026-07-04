# TASK-238: Fix is_timeout_error Reads Wrong Key (axios pattern)

## Source
Inspired by axios/axios error classification. Checking 'type' instead of
'code' misses timeout errors that only have a 'code' field.

## Goal
Fix `src/error_classifier.py` so `is_timeout_error()` checks `error['code']`.

## The bug
```python
# BUG: checks 'type' key
return error.get('type') == 'TIMEOUT'

# Fix:
return error.get('code') == 'TIMEOUT'
```

## Failing tests (3/7 fail initially)
```
test_code_timeout_only        ← FAILS ({'code':'TIMEOUT'} → bug:False, correct:True)
test_code_timeout_with_message ← FAILS ({'code':'TIMEOUT','message':'...'} → bug:False)
test_code_timeout_type_error  ← FAILS ({'code':'TIMEOUT','type':'error'} → bug:False)
```
