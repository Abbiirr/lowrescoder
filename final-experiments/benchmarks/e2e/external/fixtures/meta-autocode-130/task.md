# TASK-130: Fix Flow Node Validator Edge Direction (langflow-ai/langflow pattern)

## Source
Inspired by langflow flow graph validation. Source node validity is checked
against in-edges (incoming) instead of out-edges (outgoing), producing
wrong validity results.

## Goal
Fix `src/node_validator.py` so source nodes are validated by checking
their outgoing edge count, not incoming.

## The bug
```python
# BUG: checks in_edges for source nodes
if in_edges.get(nid, 0) == 0:

# Fix: check out_edges for source nodes
if out_edges.get(nid, 0) == 0:
```

## Failing tests (3/7 fail initially)
```
test_valid_source_with_out_edge      ← FAILS (valid source marked invalid)
test_source_with_in_edge_no_out_edge ← FAILS (invalid source marked valid)
test_one_valid_source_one_invalid    ← FAILS (both sources marked invalid)
```
