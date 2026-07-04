# TASK-164: Fix Top Contributors Ascending Sort (gitea pattern)

## Source
Inspired by go-gitea/gitea repository statistics. `sorted()` defaults to
ascending order so `[:n]` picks the LEAST active contributors instead of the
most active.

## Goal
Fix `src/repo_stats.py` so `get_top_contributors()` returns the top N authors
by commit count (highest first).

## The bug
```python
# BUG: ascending → lowest count first
ranked = sorted(counts.items(), key=lambda x: x[1])

# Fix: descending → highest count first
ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)
```

## Failing tests (3/7 fail initially)
```
test_top_1_of_3       ← FAILS ('carol' instead of 'alice')
test_top_2_of_3       ← FAILS (wrong pair)
test_top_1_two_authors ← FAILS ('eve' instead of 'dave')
```
