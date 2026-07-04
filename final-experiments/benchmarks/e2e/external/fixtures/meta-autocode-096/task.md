# TASK-096: Fix Label Matcher Case-Insensitive (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea label filtering. Label matching must be
case-insensitive.

## Goal
Fix `src/label_matcher.py` so `find_matching_labels()` compares lowercased
versions of both sides.

## The bug
```python
# BUG: case-sensitive
return [l for l in issue_labels if l in filter_labels]

# Fix:
filter_lower = {f.lower() for f in filter_labels}
return [l for l in issue_labels if l.lower() in filter_lower]
```

## Failing tests (3/7 fail initially)
```
test_uppercase_issue_label  ← FAILS ([] != ['Bug'])
test_uppercase_filter_label ← FAILS ([] != ['bug'])
test_mixed_case             ← FAILS (0 != 2)
```
