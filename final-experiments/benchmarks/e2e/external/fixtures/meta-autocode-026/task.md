# TASK-026: Fix Release Tag Semver Sort (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea release listing. Releases are displayed sorted
by semantic version, newest first. The bug uses Python's default string
sort (lexicographic), which puts 'v1.9.0' before 'v1.10.0' because '9' > '1'
character-by-character.

## Goal
Fix `src/release_sorter.py` so `sort_releases()` sorts by semantic version
(numeric comparison of MAJOR.MINOR.PATCH components), newest first.

## The bug
```python
# BUG: lexicographic sort — "v1.9.0" > "v1.10.0" incorrectly
return sorted(tags, reverse=True)

# Fix: parse version numbers and sort numerically
import re
def parse_version(tag):
    m = re.match(r'v?(\d+)\.(\d+)\.(\d+)', tag)
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)
return sorted(tags, key=parse_version, reverse=True)
```

## Failing tests (3/7 fail initially)
```
test_double_digit_minor_newest_first ← FAILS (v1.9.0 before v1.10.0)
test_double_digit_patch_newest_first ← FAILS (v1.2.9 before v1.2.10)
test_mixed_versions_correct_order    ← FAILS (v1.9.0 before v1.10.0 in list)
```
