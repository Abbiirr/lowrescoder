# TASK-088: Fix Issue Reference Extractor Keywords (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea PR issue linking. GitHub accepts `Fixes`, `Closes`,
`Resolves`, and `Fix` as closing keywords; the pattern only matches `Fixes`.

## Goal
Fix `src/issue_linker.py` so `extract_issue_refs()` matches all four keywords.

## The bug
```python
# BUG: only 'Fixes'
re.findall(r'(?:Fixes)\s+#(\d+)', text, re.IGNORECASE)

# Fix: all closing keywords
re.findall(r'(?:Fixes|Closes|Resolves|Fix)\s+#(\d+)', text, re.IGNORECASE)
```

## Failing tests (3/7 fail initially)
```
test_closes_keyword      ← FAILS ([] != [200])
test_resolves_keyword    ← FAILS ([] != [300])
test_fix_keyword_singular ← FAILS ([] != [42])
```
