# TASK-045: Fix String-to-Bool Coercion (langflow-ai/langflow pattern)

## Source
Inspired by langflow-ai/langflow component variable type coercion. When a
boolean input receives the string "false", it should return False. The bug
calls `bool("false")` which returns True because non-empty strings are always
truthy in Python.

## Goal
Fix `src/bool_coercer.py` so `coerce_to_bool()` correctly converts "false",
"False", and "0" to False.

## The bug
```python
# BUG: bool("false") = True (non-empty string is truthy)
return bool(value)

# Fix: handle string representations explicitly
if isinstance(value, str):
    return value.lower() not in ('false', '0', 'no', '')
return bool(value)
```

## Failing tests (3/7 fail initially)
```
test_string_false        ← FAILS ("false" → True, should be False)
test_string_false_capitalized ← FAILS ("False" → True)
test_string_zero         ← FAILS ("0" → True, should be False)
```
