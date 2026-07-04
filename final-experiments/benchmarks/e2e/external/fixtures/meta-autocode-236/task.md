# TASK-236: Fix get_node_inputs Reads Singular 'input' Not 'inputs' (langflow pattern)

## Source
Inspired by langflow-ai/langflow node schema. Reading 'input' (singular)
instead of 'inputs' (plural) always returns an empty list.

## Goal
Fix `src/node_inputs.py` so `get_node_inputs()` reads the `'inputs'` key.

## The bug
```python
# BUG: singular 'input'
return node.get('input', [])

# Fix:
return node.get('inputs', [])
```

## Failing tests (3/7 fail initially)
```
test_single_input ← FAILS ({'inputs':['text']} → bug:[], correct:['text'])
test_two_inputs   ← FAILS ({'inputs':['x','y']} → bug:[], correct:['x','y'])
test_input_with_name ← FAILS ({'inputs':['a'],'name':'n'} → bug:[])
```
