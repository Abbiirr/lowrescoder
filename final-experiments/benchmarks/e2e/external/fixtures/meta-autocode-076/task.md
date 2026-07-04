# TASK-076: Fix OAuth2 Scope Subset Check (fastapi/fastapi pattern)

## Source
Inspired by FastAPI OAuth2 security scopes. `has_required_scopes` must verify
that ALL required scopes are present in the token, not just that any one
overlaps. The bug uses intersection (any overlap) instead of subset (all
required present).

## Goal
Fix `src/scope_checker.py` so `has_required_scopes()` returns `True` only
when `token_scopes` is a superset of `required_scopes`.

## The bug
```python
# BUG: any overlap → True (grants partial scope as full access)
return bool(set(token_scopes) & set(required_scopes))

# Fix: all required must be present
return set(required_scopes).issubset(set(token_scopes))
```

## Failing tests (3/7 fail initially)
```
test_partial_match_insufficient  ← FAILS (token=['read'], required=['read','write'] → True, should be False)
test_one_of_two_scopes_missing   ← FAILS (token=['admin'], required=['read','admin'] → True, should be False)
test_empty_required_returns_true ← FAILS (required=[] → False, should be True)
```
