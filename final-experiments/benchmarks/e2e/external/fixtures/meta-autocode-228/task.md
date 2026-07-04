# TASK-228: Fix normalize_path Creates Double Slash (fastapi pattern)

## Source
Inspired by fastapi/fastapi path normalization. Always prepending '/'
creates '//path' when input already starts with '/'.

## Goal
Fix `src/path_normalizer.py` so `normalize_path()` does not double the
leading slash.

## The bug
```python
# BUG: unconditional prepend
return '/' + path

# Fix:
return path if path.startswith('/') else '/' + path
```

## Failing tests (3/7 fail initially)
```
test_already_slash  ← FAILS ('/users' → bug:'//users', correct:'/users')
test_already_nested ← FAILS ('/api/v1' → bug:'//api/v1', correct:'/api/v1')
test_just_slash     ← FAILS ('/' → bug:'//', correct:'/')
```
