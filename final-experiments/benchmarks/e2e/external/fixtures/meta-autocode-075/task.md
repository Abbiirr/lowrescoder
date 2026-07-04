# TASK-075: Fix URL Param List Encoding (axios/axios pattern)

## Source
Inspired by axios/axios URL parameter serialization. List values must be
encoded as repeated keys (`ids=1&ids=2&ids=3`), not comma-joined
(`ids=1,2,3`). The bug uses str.join(',') for list values.

## Goal
Fix `src/param_encoder.py` so `encode_params()` repeats the key for each
list item.

## The bug
```python
# BUG: comma-joined
parts.append(f"{key}={','.join(str(v) for v in value)}")

# Fix: repeat key
for v in value:
    parts.append(f"{key}={v}")
```

## Failing tests (3/7 fail initially)
```
test_list_repeated_key      ← FAILS ('ids=1,2,3' instead of 'ids=1&ids=2&ids=3')
test_list_two_string_values ← FAILS ('tag=python,web' instead of 'tag=python&tag=web')
test_mixed_list_and_scalar  ← FAILS ('ids=1,2' not in result)
```
