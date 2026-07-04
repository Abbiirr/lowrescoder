# TASK-064: Fix Commit Message Length Warning Threshold (jesseduffield/lazygit pattern)

## Source
Inspired by jesseduffield/lazygit commit message linting. The conventional Git
subject-line limit is 50 characters (warn at > 50). The bug warns only beyond
72 characters, silently passing 51-72 character subjects.

## Goal
Fix `src/commit_checker.py` so `check_commit_message()` appends a warning
when `len(first_line) > 50`.

## The bug
```python
# BUG: warns only beyond 72 chars
if len(first_line) > 72:
    warnings.append('...')

# Fix: correct limit
if len(first_line) > 50:
    warnings.append('...')
```

## Failing tests (3/7 fail initially)
```
test_51_chars_warns ← FAILS (51-char subject: bug silent, fix warns)
test_60_chars_warns ← FAILS (60-char subject: bug silent, fix warns)
test_72_chars_warns ← FAILS (72-char subject: bug silent, fix warns)
```
