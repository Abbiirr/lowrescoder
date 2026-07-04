# TASK-248: Fix get_repo_language() Wrong Key 'lang' vs 'language' (gitea pattern)

## Source
Inspired by go-gitea/gitea repository API. Repo info uses 'language', not 'lang'.

## Goal
Fix `src/repo_language.py` so `get_repo_language()` reads the correct `'language'` key.

## The bug
```python
# BUG: wrong key
return repo.get('lang', default)

# Fix:
return repo.get('language', default)
```

## Failing tests (3/7 fail initially)
```
test_python     ← FAILS ({'language': 'Python'} → bug:'Unknown', correct:'Python')
test_go_with_stars ← FAILS ({'language': 'Go'} → bug:'Unknown', correct:'Go')
test_typescript ← FAILS ({'language': 'TypeScript'} → bug:'Unknown', correct:'TypeScript')
```
