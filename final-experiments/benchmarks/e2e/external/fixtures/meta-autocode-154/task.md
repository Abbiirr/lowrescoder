# TASK-154: Fix Git Tag Ref Detection Typo (lazygit pattern)

## Source
Inspired by jesseduffield/lazygit ref resolution. A typo drops the 's' from
`refs/tags/`, making `is_tag_ref()` always return False for valid tag refs.

## Goal
Fix `src/ref_checker.py` so `is_tag_ref()` correctly identifies tag references.

## The bug
```python
# BUG: 'refs/tag/' is missing 's' — never matches
return ref.startswith('refs/tag/')

# Fix:
return ref.startswith('refs/tags/')
```

## Failing tests (3/7 fail initially)
```
test_version_tag  ← FAILS (False instead of True)
test_latest_tag   ← FAILS (False instead of True)
test_release_tag  ← FAILS (False instead of True)
```
