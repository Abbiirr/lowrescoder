# TASK-065: Fix Release Tag Semver Validation (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea release creation. Release tags must follow semver
format `vX.Y.Z` (e.g. `v1.2.3`). The bug only checks that the tag is
non-empty, accepting arbitrary strings like `'release'` or `'1.2.3'`.

## Goal
Fix `src/tag_validator.py` so `is_valid_release_tag()` uses a regex to
require `^v\d+\.\d+\.\d+$`.

## The bug
```python
# BUG: any non-empty string accepted
return bool(tag)

# Fix: enforce semver format
return bool(re.match(r'^v\d+\.\d+\.\d+$', tag))
```

## Failing tests (3/7 fail initially)
```
test_no_v_prefix_rejected   ← FAILS ('1.2.3' accepted, should be rejected)
test_plain_string_rejected  ← FAILS ('release' accepted, should be rejected)
test_partial_semver_rejected ← FAILS ('v1.2' accepted, should be rejected)
```
