# TASK-227: Fix count_output_edges Counts All Edges Not Just Source (langflow pattern)

## Source
Inspired by langflow-ai/langflow graph edge traversal. Returning len(edges)
instead of filtering by source node gives wrong output-degree counts.

## Goal
Fix `src/edge_counter.py` so `count_output_edges()` counts only edges
where `edge['source'] == node_id`.

## The bug
```python
# BUG: no source filter
return len(edges)

# Fix:
return sum(1 for e in edges if e.get('source') == node_id)
```

## Failing tests (3/7 fail initially)
```
test_one_match_one_other ← FAILS (1 matching + 1 other → bug:2, correct:1)
test_zero_matches        ← FAILS (0 matching + 2 others → bug:2, correct:0)
test_one_of_three        ← FAILS (1 matching + 2 others → bug:3, correct:1)
```
