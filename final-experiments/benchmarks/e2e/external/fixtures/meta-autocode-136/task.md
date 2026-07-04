# TASK-136: Fix Tag Sorter Count Order (usememos/memos pattern)

## Source
Inspired by memos tag cloud sorting. Count-based sort uses ascending
order instead of descending, so least-used tags appear first.

## Goal
Fix `src/tag_sorter.py` so `sort_tags(by='count')` returns tags in
descending order by count.

## The bug
```python
# BUG: ascending sort
return sorted(tags, key=lambda t: t.get('count', 0))

# Fix: descending
return sorted(tags, key=lambda t: t.get('count', 0), reverse=True)
```

## Failing tests (3/7 fail initially)
```
test_sort_by_count_descending  ← FAILS ([1,3,5] instead of [5,3,1])
test_highest_count_first       ← FAILS (lowest first)
test_count_sort_three_descending ← FAILS (wrong order)
```
