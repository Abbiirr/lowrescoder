# TASK-190: Fix Branch Name Extraction Truncates Nested Branches (lazygit pattern)

## Source
Inspired by jesseduffield/lazygit ref parsing. Using `split('/')[-1]` returns
only the last path segment, so `'refs/heads/feature/my-branch'` incorrectly
becomes `'my-branch'` instead of `'feature/my-branch'`.

## Goal
Fix `src/ref_parser.py` so `branch_from_ref()` returns everything after the
`refs/heads/` prefix.

## The bug
```python
# BUG: last segment only
return ref.split('/')[-1]

# Fix:
return ref.split('refs/heads/', 1)[-1]
```

## Failing tests (3/7 fail initially)
```
test_feature_branch ← FAILS ('refs/heads/feature/my-branch' → bug 'my-branch')
test_bugfix_branch  ← FAILS ('refs/heads/bugfix/issue-123' → bug 'issue-123')
test_deep_branch    ← FAILS ('refs/heads/user/john/task' → bug 'task')
```
