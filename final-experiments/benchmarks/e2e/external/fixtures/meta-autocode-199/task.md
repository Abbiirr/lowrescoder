# TASK-199: Fix Conventional Commit Type Case-Sensitive Check (lazygit pattern)

## Source
Inspired by jesseduffield/lazygit commit message parsing. The type lookup is
case-sensitive, so `'Feat: ...'` and `'FIX: ...'` are not recognised as
conventional commits.

## Goal
Fix `src/commit_checker.py` so `is_conventional_commit()` normalises the
type to lowercase before looking it up.

## The bug
```python
# BUG: case-sensitive
return type_part in _TYPES

# Fix:
return type_part.lower() in _TYPES
```

## Failing tests (3/7 fail initially)
```
test_capitalised_feat ← FAILS ('Feat: add login' → bug False)
test_uppercase_fix    ← FAILS ('FIX: resolve crash' → bug False)
test_mixed_docs       ← FAILS ('Docs: update readme' → bug False)
```
