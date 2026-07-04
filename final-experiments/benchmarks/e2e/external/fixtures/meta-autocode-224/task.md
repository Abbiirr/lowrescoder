# TASK-224: Fix is_memo_public Checks Lowercase 'public' Not 'PUBLIC' (memos pattern)

## Source
Inspired by usememos/memos visibility system. The API returns visibility as
uppercase 'PUBLIC'; comparing to lowercase 'public' always returns False.

## Goal
Fix `src/memo_visibility.py` so `is_memo_public()` returns True when
`memo['visibility'] == 'PUBLIC'`.

## The bug
```python
# BUG: wrong case
return memo.get('visibility') == 'public'

# Fix:
return memo.get('visibility') == 'PUBLIC'
```

## Failing tests (3/7 fail initially)
```
test_public           ← FAILS ({'visibility':'PUBLIC'} → bug:False, correct:True)
test_public_with_id   ← FAILS ({'visibility':'PUBLIC','id':1} → bug:False)
test_public_with_content ← FAILS ({'visibility':'PUBLIC','content':'hi'} → bug:False)
```
