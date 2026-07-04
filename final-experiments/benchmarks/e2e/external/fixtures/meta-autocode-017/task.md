# TASK-017: Fix Flow Node Topological Sort (langflow-ai/langflow pattern)

## Source
Inspired by langflow-ai/langflow DAG execution engine.
When building a flow graph with multiple independent source nodes,
the executor must process ALL sources — not just the first one in the list.

## Goal
Fix `src/flow_sorter.py` so `topological_sort()` seeds the BFS queue from
**all** zero-in-degree nodes, not only `nodes[0]`.

## The bug
```python
# BUG: only first node seeds the queue — other sources and their
# downstream nodes are silently omitted from the result
queue = deque([nodes[0]])

# Fix: seed from every node with no incoming edges
queue = deque(n for n in nodes if in_degree[n] == 0)
```

## Failing tests (3/7 fail initially)
```
test_multiple_sources      ← FAILS (only A returned, B,C,D missing)
test_disconnected_chains   ← FAILS (only A,B returned, C,D missing)
test_no_edges_all_returned ← FAILS (only X returned, Y,Z missing)
```
