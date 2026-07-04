# TASK-149: Fix Memo Tag Search Case-Sensitivity (memos pattern)

## Source
Inspired by usememos/memos tag filtering. Tag lookup is case-sensitive so
searching for "Python" misses memos tagged "python" and vice versa.

## Goal
Fix `src/memo_tagger.py` so `find_memos_by_tag()` matches tags
case-insensitively.

## The bug
```python
# BUG: case-sensitive — 'Python' not in ['python']
return [m for m in memos if tag in m.get('tags', [])]

# Fix: lowercase both sides
return [m for m in memos if tag.lower() in [t.lower() for t in m.get('tags', [])]]
```

## Failing tests (3/7 fail initially)
```
test_uppercase_tag_query   ← FAILS ('Python' not in ['python'] → [])
test_uppercase_stored_tag  ← FAILS ('python' not in ['PYTHON'] → [])
test_mixed_case            ← FAILS ('python' not in ['PyThOn'] → [])
```
