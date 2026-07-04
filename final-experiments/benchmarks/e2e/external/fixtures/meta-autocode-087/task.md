# TASK-087: Fix Git Branch Name Double-Dot Validation (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea branch name validation. Git forbids `..` in branch
names but the validator doesn't check for it.

## Goal
Fix `src/branch_checker.py` so `is_valid_branch_name()` rejects names
containing `..`.

## The bug
```python
# BUG: missing double-dot check
invalid_patterns = [
    r'[\s~^:?*\[\\\x00-\x1f\x7f]',
    r'^/',
    r'/$',
    r'\.lock$',
]

# Fix: add r'\.\.' to invalid_patterns
```

## Failing tests (3/7 fail initially)
```
test_double_dot_invalid            ← FAILS (True != False)
test_double_dot_at_start_invalid   ← FAILS (True != False)
test_dotlock_with_double_dot_invalid ← FAILS (True != False)
```
