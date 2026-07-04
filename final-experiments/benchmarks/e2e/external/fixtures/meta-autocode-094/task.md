# TASK-094: Fix Release Version Separator (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea release tagging. Semantic versions use dots (`.`)
not dashes (`-`) as the separator between major.minor.patch.

## Goal
Fix `src/release_namer.py` so `generate_release_name()` produces `v1.2.3`
format instead of `v1-2-3`.

## The bug
```python
# BUG: dash separator
tag = f"v{major}-{minor}-{patch}"

# Fix: dot separator
tag = f"v{major}.{minor}.{patch}"
```

## Failing tests (3/7 fail initially)
```
test_dot_separated_version  ← FAILS ('v1-2-3' != 'v1.2.3')
test_single_digit_version   ← FAILS ('v0-1-0' != 'v0.1.0')
test_pre_release_format     ← FAILS ('v1-0-0-pre' != 'v1.0.0-pre')
```
