# TASK-072: Fix Component Metadata Description Validation (langflow-ai/langflow pattern)

## Source
Inspired by langflow-ai/langflow component registration. Both `name` and
`description` are required fields. The bug only validates `name`, silently
accepting components with empty/missing descriptions.

## Goal
Fix `src/component_validator.py` so `validate_component_metadata()` also
appends an error when `description` is falsy.

## The bug
```python
# BUG: description never validated
if not metadata.get('name'):
    errors.append('name is required')

# Fix: validate both
if not metadata.get('name'):
    errors.append('name is required')
if not metadata.get('description'):
    errors.append('description is required')
```

## Failing tests (3/7 fail initially)
```
test_empty_description_detected     ← FAILS (description='' → no error)
test_none_description_detected      ← FAILS (description=None → no error)
test_missing_description_key_detected ← FAILS (no 'description' key → no error)
```
