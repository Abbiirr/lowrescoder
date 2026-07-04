# TASK-215: Fix get_memo_tags Reads Wrong Key (memos pattern)

## Source
Inspired by usememos/memos tag system. Using 'tag' instead of 'tags'
silently returns an empty list for every memo regardless of its actual tags.

## Goal
Fix `src/memo_tags.py` so `get_memo_tags()` reads the correct `'tags'` key.

## The bug
```python
# BUG: wrong key 'tag'
return memo.get('tag', [])

# Fix:
return memo.get('tags', [])
```

## Failing tests (3/7 fail initially)
```
test_single_tag ← FAILS ({'tags': ['python']} → bug:[], correct:['python'])
test_two_tags   ← FAILS ({'tags': ['a','b']} → bug:[], correct:['a','b'])
test_three_tags ← FAILS ({'tags': ['x','y','z']} → bug:[], correct:['x','y','z'])
```
