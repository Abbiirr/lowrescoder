# TASK-115: Fix Email Validator TLD Length (fastapi/fastapi pattern)

## Source
Inspired by fastapi/fastapi request validation. The email regex requires
exactly 2-character TLDs, rejecting .com, .org, .info, etc.

## Goal
Fix `src/format_checker.py` so `is_valid_email()` accepts TLDs of 2 or
more characters.

## The bug
```python
# BUG: {2} means exactly 2 chars
pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2}$'

# Fix: {2,} means 2 or more
pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
```

## Failing tests (3/7 fail initially)
```
test_com_tld       ← FAILS (False != True; .com has 3 chars)
test_org_tld       ← FAILS (False != True)
test_io_and_long   ← FAILS (False != True; .info has 4 chars)
```
