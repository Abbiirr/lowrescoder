# TASK-106: Fix Diff Renderer Context Line Prefix (sharkdp/bat pattern)

## Source
Inspired by sharkdp/bat diff rendering. Context lines in unified diff format
must be prefixed with a space character, not an empty string.

## Goal
Fix `src/diff_renderer.py` so `render_diff_line()` prefixes context lines
with `' '` (space).

## The bug
```python
# BUG: no prefix for context/unchanged lines
else:
    return line

# Fix:
else:
    return ' ' + line
```

## Failing tests (3/7 fail initially)
```
test_context_line_has_space_prefix ← FAILS ('context' != ' context')
test_context_line_length           ← FAILS (3 != 4)
test_unchanged_line_prefix         ← FAILS ('foo bar' != ' foo bar')
```
