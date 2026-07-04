# TASK-051: Fix Content Truncation Ellipsis (usememos/memos pattern)

## Source
Inspired by usememos/memos memo list view which truncates long content with
an ellipsis. The bug performs the truncation but omits the trailing `'...'`.

## Goal
Fix `src/content_truncator.py` so `truncate_content()` appends `'...'` when
content exceeds `max_length`.

## The bug
```python
# BUG: no ellipsis
return content[:max_length]

# Fix: append ellipsis
return content[:max_length] + '...'
```

## Failing tests (3/7 fail initially)
```
test_long_content_gets_ellipsis      ← FAILS ('hello world...' missing '...')
test_truncation_at_word_boundary     ← FAILS ('abc...' missing '...')
test_truncation_preserves_prefix_length ← FAILS (20 x's missing '...')
```
