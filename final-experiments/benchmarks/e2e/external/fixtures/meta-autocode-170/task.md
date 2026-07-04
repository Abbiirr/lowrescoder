# TASK-170: Fix Pre-Release Version Detection (gitea pattern)

## Source
Inspired by go-gitea/gitea release management. Pre-release versions use `-`
per semver (e.g., `1.0.0-alpha`), but the bug checks for `+` (build metadata
marker) — all pre-releases return False.

## Goal
Fix `src/version_checker.py` so `is_prerelease()` checks for `-` not `+`.

## The bug
```python
# BUG: '+' is build metadata, not pre-release
return '+' in version

# Fix:
return '-' in version
```

## Failing tests (3/7 fail initially)
```
test_alpha_prerelease ← FAILS (False instead of True)
test_beta_prerelease  ← FAILS (False instead of True)
test_rc_prerelease    ← FAILS (False instead of True)
```
