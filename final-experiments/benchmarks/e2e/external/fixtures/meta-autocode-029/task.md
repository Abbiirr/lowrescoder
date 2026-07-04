# TASK-029: Fix Branch Name Validator Dot Check (jesseduffield/lazygit pattern)

## Source
Inspired by jesseduffield/lazygit branch name validation. Git allows dots in
branch names (e.g. `v1.0`, `release.2026`) but forbids consecutive dots `..`.
The bug checks `'.' in name` (any dot), which incorrectly rejects valid names
like `v1.0`.

## Goal
Fix `src/branch_validator.py` so `is_valid_branch_name()` only rejects double
dots (`..`), not single dots.

## The bug
```python
# BUG: rejects any dot — only '..' (double-dot) is forbidden in git refs
if '.' in name:
    return False

# Fix: check for double-dot only
if '..' in name:
    return False
```

## Failing tests (3/7 fail initially)
```
test_version_branch_with_dot  ← FAILS ("v1.0" rejected)
test_path_style_with_dot      ← FAILS ("hotfix/fix-1.5" rejected)
test_dotfile_style_branch     ← FAILS ("release.2026" rejected)
```
