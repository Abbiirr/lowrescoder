# TASK-069: Fix Memo Default Visibility (usememos/memos pattern)

## Source
Inspired by usememos/memos memo creation. New memos should default to
`'private'` visibility. The bug defaults to `'public'`, which would
accidentally expose all memos to other users.

## Goal
Fix `src/memo_creator.py` so `create_memo()` uses `'private'` as the
fallback when `visibility` is not specified.

## The bug
```python
# BUG: defaults to 'public'
'visibility': visibility or 'public',

# Fix: default to 'private'
'visibility': visibility or 'private',
```

## Failing tests (3/7 fail initially)
```
test_default_visibility_is_private       ← FAILS (defaults to 'public', expected 'private')
test_none_visibility_defaults_to_private ← FAILS (None → 'public', expected 'private')
test_empty_string_visibility_defaults_to_private ← FAILS ('' → 'public', expected 'private')
```
