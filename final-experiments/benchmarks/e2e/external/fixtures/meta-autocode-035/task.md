# TASK-035: Fix Repeated Query Parameter List Parsing (fastapi/fastapi pattern)

## Source
Inspired by fastapi/fastapi List query parameter handling. When a route
declares `tags: List[str]`, FastAPI should collect all `?tag=` values from
the URL. The bug uses a dict assignment that overwrites on each repetition,
keeping only the last value.

## Goal
Fix `src/query_list.py` so `parse_list_query_param()` collects all occurrences
into a list.

## The bug
```python
# BUG: dict assignment overwrites previous value
result[param_name] = v

# Fix: collect into a list
if param_name not in result:
    result[param_name] = []
result[param_name].append(v)
# And return result.get(param_name, [])
```

## Failing tests (3/7 fail initially)
```
test_multiple_values         ← FAILS (?tag=a&tag=b&tag=c → ['c'])
test_two_values              ← FAILS (?tag=python&tag=rust → ['rust'])
test_mixed_params_with_list  ← FAILS (?x=1&tag=a&y=2&tag=b → ['b'])
```
