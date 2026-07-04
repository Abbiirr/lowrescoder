# TASK-061: Fix Issue Comment Counter (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea issue API. The comment count on an issue should
only include top-level comments, not threaded replies (which have a
`parent_id`). The bug counts all comment objects regardless.

## Goal
Fix `src/comment_counter.py` so `count_issue_comments()` counts only
comments where `parent_id is None`.

## The bug
```python
# BUG: counts replies too
return len(comments)

# Fix: filter to top-level only
return sum(1 for c in comments if c.get('parent_id') is None)
```

## Failing tests (3/7 fail initially)
```
test_replies_excluded         ← FAILS ([top, reply, reply] returns 3, expected 1)
test_all_replies              ← FAILS ([reply, reply] returns 2, expected 0)
test_mixed_top_and_replies    ← FAILS ([top, top, reply, top, reply] returns 5, expected 3)
```
