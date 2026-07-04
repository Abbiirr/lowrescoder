# TASK-218: Fix is_valid_component_id Rejects Underscores (langflow pattern)

## Source
Inspired by langflow-ai/langflow component ID validation. Using `isalnum()`
rejects underscores that are valid in component IDs.

## Goal
Fix `src/component_id.py` so `is_valid_component_id()` also accepts
underscore characters.

## The bug
```python
# BUG: isalnum() rejects '_'
return bool(cid) and cid.isalnum()

# Fix:
return bool(cid) and all(c.isalnum() or c == '_' for c in cid)
```

## Failing tests (3/7 fail initially)
```
test_with_underscore  ← FAILS ('my_component' → bug:False, correct:True)
test_underscore_number ← FAILS ('node_1' → bug:False, correct:True)
test_multi_underscore  ← FAILS ('chat_model_v2' → bug:False, correct:True)
```
