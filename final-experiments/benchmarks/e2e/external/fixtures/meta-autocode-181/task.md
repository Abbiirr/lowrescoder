# TASK-181: Fix Short Hash Returns 6 Chars Instead of 7 (lazygit pattern)

## Source
Inspired by jesseduffield/lazygit commit display. The conventional git short
hash is 7 characters, but the implementation slices only 6.

## Goal
Fix `src/hash_utils.py` so `short_hash()` returns the first 7 characters of
the commit hash.

## The bug
```python
# BUG: 6 chars instead of 7
return commit_hash[:6]

# Fix:
return commit_hash[:7]
```

## Failing tests (3/7 fail initially)
```
test_seven_chars ← FAILS ('abcdefg' → bug returns 'abcdef')
test_twelve_chars ← FAILS (12-char hash → bug returns 6, fix returns 7)
test_full_hash   ← FAILS (full 40-char SHA → bug returns 6 chars)
```
