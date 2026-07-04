# TASK-197: Fix Latest Memo Returns Oldest Due to Ascending Sort (memos pattern)

## Source
Inspired by usememos/memos feed ordering. Sorting in ascending order and
taking `[0]` returns the memo with the smallest timestamp (oldest), not the
largest (most recent).

## Goal
Fix `src/memo_sorter.py` so `get_latest_memo()` returns the memo with the
highest `updated_at` value.

## The bug
```python
# BUG: ascending sort — [0] is oldest
return sorted(memos, key=lambda m: m.get('updated_at', 0))[0]

# Fix:
return sorted(memos, key=lambda m: m.get('updated_at', 0), reverse=True)[0]
# or: return max(memos, key=lambda m: m.get('updated_at', 0))
```

## Failing tests (3/7 fail initially)
```
test_returns_latest_not_oldest ← FAILS (bug returns oldest memo)
test_unsorted_input            ← FAILS (bug returns memo with smallest ts)
test_reversed_input            ← FAILS (bug returns oldest)
```
