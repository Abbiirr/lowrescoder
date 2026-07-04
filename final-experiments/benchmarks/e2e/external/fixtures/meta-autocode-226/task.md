# TASK-226: Fix abbreviate_branch Missing Ellipsis on Truncation (lazygit pattern)

## Source
Inspired by jesseduffield/lazygit branch display. Long branch names are
silently truncated without adding '...' to signal the truncation.

## Goal
Fix `src/branch_abbreviator.py` so `abbreviate_branch()` appends `'...'`
when truncating, keeping the total length at max_len.

## The bug
```python
# BUG: no ellipsis
return name[:max_len]

# Fix:
return name[:max_len - 3] + '...'
```

## Failing tests (3/7 fail initially)
```
test_long_repeated ← FAILS ('a'*25 → bug:'a'*20, correct:'a'*17+'...')
test_long_feature  ← FAILS (35-char name → bug truncates to 20, correct adds '...')
test_long_release  ← FAILS (25-char name → bug truncates to 20, correct adds '...')
```
