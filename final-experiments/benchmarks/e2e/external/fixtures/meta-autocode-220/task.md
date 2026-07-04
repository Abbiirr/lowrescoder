# TASK-220: Fix strip_auth_header Case-Sensitive Key Check (axios pattern)

## Source
Inspired by axios/axios header handling. HTTP headers are case-insensitive;
a case-sensitive removal misses 'authorization' and 'AUTHORIZATION' variants.

## Goal
Fix `src/header_utils.py` so `strip_auth_header()` removes any Authorization
header regardless of key casing.

## The bug
```python
# BUG: case-sensitive comparison
return {k: v for k, v in headers.items() if k != 'Authorization'}

# Fix:
return {k: v for k, v in headers.items() if k.lower() != 'authorization'}
```

## Failing tests (3/7 fail initially)
```
test_lowercase     ← FAILS ({'authorization':'Bearer abc'} → bug keeps it)
test_uppercase     ← FAILS ({'AUTHORIZATION':'x'} → bug keeps it)
test_mixed_case_both ← FAILS (both keys → bug keeps 'authorization')
```
