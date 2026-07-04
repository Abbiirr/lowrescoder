# TASK-175: Fix HTTPS URL Check Missing Scheme Separator (axios pattern)

## Source
Inspired by axios/axios URL security checks. Checking `startswith('https')`
without requiring `://` incorrectly accepts strings like 'httpsexample.com'
as secure HTTPS URLs.

## Goal
Fix `src/url_utils.py` so `is_secure_url()` requires the full scheme prefix
`https://`.

## The bug
```python
# BUG: 'httpsexample.com' passes — missing '://'
return url.startswith('https')

# Fix:
return url.startswith('https://')
```

## Failing tests (3/7 fail initially)
```
test_https_no_scheme_separator ← FAILS ('httpsexample.com' incorrectly True)
test_https_no_slashes          ← FAILS ('httpsfoo' incorrectly True)
test_https_bare_prefix         ← FAILS ('https' incorrectly True)
```
