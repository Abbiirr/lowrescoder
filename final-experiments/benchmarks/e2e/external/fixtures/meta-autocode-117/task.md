# TASK-117: Fix Clone URL Builder HTTPS vs SSH (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea repository clone URL generation. The HTTPS branch
uses the SSH format (`git@host:owner/repo.git`) instead of `https://host/owner/repo.git`.

## Goal
Fix `src/repo_cloner.py` so `build_clone_url()` returns the correct HTTPS URL.

## The bug
```python
# BUG: SSH format used for https too
return f"git@{host}:{owner}/{repo}.git"

# Fix:
return f"https://{host}/{owner}/{repo}.git"
```

## Failing tests (3/7 fail initially)
```
test_https_url                ← FAILS ('git@...' != 'https://...')
test_default_protocol_is_https ← FAILS (starts with 'git@')
test_https_no_at_sign         ← FAILS ('@' found in result)
```
