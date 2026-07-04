# TASK-212: Fix count_open_issues Counts Closed Issues (gitea pattern)

## Source
Inspired by go-gitea/gitea issue listing. Function returns total count
instead of filtering to open issues only.

## Goal
Fix `src/issue_counter.py` so `count_open_issues()` counts only
issues where `state == 'open'`.

## The bug
```python
# BUG: no state filter
return len(issues)

# Fix:
return sum(1 for i in issues if i.get('state') == 'open')
```

## Failing tests (3/7 fail initially)
```
test_mixed         ← FAILS (1 open + 1 closed = bug:2, correct:1)
test_all_closed_one ← FAILS (0 open + 1 closed = bug:1, correct:0)
test_all_closed_two ← FAILS (0 open + 2 closed = bug:2, correct:0)
```
