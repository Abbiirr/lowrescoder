# TASK-233: Fix get_memo_author Reads Wrong Key (memos pattern)

## Source
Inspired by usememos/memos memo author lookup. Reading 'creator' instead
of 'author' always returns None.

## Goal
Fix `src/memo_author.py` so `get_memo_author()` reads the `'author'` key.

## The bug
```python
# BUG: wrong key 'creator'
creator = memo.get('creator', {})
return creator.get('username')

# Fix:
author = memo.get('author', {})
return author.get('username')
```

## Failing tests (3/7 fail initially)
```
test_author_alice       ← FAILS ({'author':{'username':'alice'}} → bug:None)
test_author_with_id     ← FAILS ({'author':{'username':'bob'},'id':1} → bug:None)
test_author_with_content ← FAILS ({'author':{'username':'carol'},...} → bug:None)
```
