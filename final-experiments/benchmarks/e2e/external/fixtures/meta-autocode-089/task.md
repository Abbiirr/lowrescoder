# TASK-089: Fix Flow Nodes Type Validation (langflow-ai/langflow pattern)

## Source
Inspired by langflow-ai/langflow flow validation. The validator must check that
`nodes` is actually a list before checking its length.

## Goal
Fix `src/flow_validator.py` so `validate_flow_inputs()` emits an error when
`nodes` is not a list.

## The bug
```python
# BUG: len() works on strings/dicts too, so type check is skipped
nodes = flow.get('nodes', [])
if len(nodes) == 0:
    errors.append('flow must have at least one node')

# Fix: check type first
nodes = flow.get('nodes', [])
if not isinstance(nodes, list):
    errors.append('nodes must be a list')
elif len(nodes) == 0:
    errors.append('flow must have at least one node')
```

## Failing tests (3/7 fail initially)
```
test_nodes_as_string_invalid  ← FAILS (no 'nodes' error in errors)
test_nodes_as_dict_invalid    ← FAILS (no 'nodes' error in errors)
test_nodes_as_integer_invalid ← FAILS (TypeError or no error)
```
