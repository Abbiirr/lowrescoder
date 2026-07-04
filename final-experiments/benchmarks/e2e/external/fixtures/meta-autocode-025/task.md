# TASK-025: Fix Memo Search Case Sensitivity (usememos/memos pattern)

## Source
Inspired by usememos/memos search feature. Users expect search to be
case-insensitive — searching "PYTHON" should find memos with "python".
The bug uses Python's `in` operator which is case-sensitive.

## Goal
Fix `src/memo_search.py` so `search_memo()` performs case-insensitive
substring matching.

## The bug
```python
# BUG: case-sensitive — "PYTHON" not in "python project notes"
return query in content

# Fix: lowercase both sides
return query.lower() in content.lower()
```

## Failing tests (3/7 fail initially)
```
test_uppercase_query_finds_lowercase_content ← FAILS ("PYTHON" vs "python")
test_lowercase_query_finds_uppercase_content ← FAILS ("meeting" vs "Meeting")
test_mixed_case_query_and_content            ← FAILS ("Todo" vs "TODO")
```
