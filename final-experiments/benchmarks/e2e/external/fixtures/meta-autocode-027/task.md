# TASK-027: Fix Flow Node Type Validator Any Wildcard (langflow-ai/langflow pattern)

## Source
Inspired by langflow-ai/langflow node connection validation. When a node
output or input has type 'Any', it should connect with any other type.
The bug uses exact equality so 'str' != 'Any' and connections to/from 'Any'
typed ports are incorrectly rejected.

## Goal
Fix `src/type_validator.py` so `can_connect()` treats 'Any' as a wildcard
on either side of the connection.

## The bug
```python
# BUG: exact match only — 'Any' wildcard not handled
return output_type == input_type

# Fix: treat 'Any' as wildcard
if output_type == "Any" or input_type == "Any":
    return True
return output_type == input_type
```

## Failing tests (3/7 fail initially)
```
test_str_output_to_any_input   ← FAILS ("str" → "Any" rejected)
test_any_output_to_str_input   ← FAILS ("Any" → "str" rejected)
test_any_output_to_list_input  ← FAILS ("Any" → "List[str]" rejected)
```
