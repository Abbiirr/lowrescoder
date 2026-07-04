# TASK-093: Fix PR Merge Check Key Name (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea pull request merge gate. The correct approval key
is `review_approved`, but the bug checks `approved`.

## Goal
Fix `src/pr_merger.py` so `can_merge_pr()` checks `pr.get('review_approved')`.

## The bug
```python
# BUG: wrong key name
pr.get('approved', False)

# Fix:
pr.get('review_approved', False)
```

## Failing tests (3/7 fail initially)
```
test_review_approved_basic         ← FAILS (False != True; 'approved' absent)
test_review_approved_with_extra    ← FAILS (False != True)
test_review_approved_second_reviewer ← FAILS (False != True)
```
