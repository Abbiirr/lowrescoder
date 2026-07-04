# TASK-245: Fix get_node_outputs() Wrong Key 'output' vs 'outputs' (langflow pattern)

## Source
Inspired by langflow-ai/langflow node data model. Node uses 'outputs' (plural), not 'output'.

## Goal
Fix `src/node_outputs.py` so `get_node_outputs()` reads the correct `'outputs'` key.

## The bug
```python
# BUG: wrong key (singular)
return node.get('output', [])

# Fix:
return node.get('outputs', [])
```

## Failing tests (3/7 fail initially)
```
test_single_output   ← FAILS ({'outputs': ['result']} → bug:[], correct:['result'])
test_multiple_outputs ← FAILS ({'outputs': ['a','b']} → bug:[], correct:['a','b'])
test_output_with_type ← FAILS ({'outputs': ['out1'],...} → bug:[], correct:['out1'])
```
