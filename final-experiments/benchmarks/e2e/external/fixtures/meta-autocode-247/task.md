# TASK-247: Fix get_response_data() Wrong Key 'payload' vs 'data' (axios pattern)

## Source
Inspired by axios/axios response object. Axios response uses 'data', not 'payload'.

## Goal
Fix `src/response_data.py` so `get_response_data()` reads the correct `'data'` key.

## The bug
```python
# BUG: wrong key
return response.get('payload', default)

# Fix:
return response.get('data', default)
```

## Failing tests (3/7 fail initially)
```
test_data_dict   ← FAILS ({'data': {'id':1}} → bug:None, correct:{'id':1})
test_data_list   ← FAILS ({'data': [1,2,3]} → bug:None, correct:[1,2,3])
test_data_string ← FAILS ({'data': 'ok'} → bug:None, correct:'ok')
```
