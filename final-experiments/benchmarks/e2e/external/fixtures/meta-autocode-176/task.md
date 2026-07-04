# TASK-176: Fix Commit Message Formatter Whitespace Leakage (gitea pattern)

## Source
Inspired by go-gitea/gitea commit message formatting utilities. The formatter
passes the message through verbatim, leaking leading/trailing whitespace into
the output.

## Goal
Fix `src/commit_formatter.py` so `format_commit()` strips surrounding
whitespace from `message` before formatting.

## The bug
```python
# BUG: whitespace not stripped
return f"{prefix}: {message}"

# Fix:
return f"{prefix}: {message.strip()}"
```

## Failing tests (3/7 fail initially)
```
test_leading_spaces   ← FAILS (leading spaces preserved in output)
test_trailing_spaces  ← FAILS (trailing spaces preserved in output)
test_newline_in_message ← FAILS (newlines preserved in output)
```
