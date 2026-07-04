# TASK-174: Fix Word Count Splitting on Literal Space (fastapi pattern)

## Source
Inspired by fastapi/fastapi text processing utilities. Splitting on a literal
space character fails for empty strings, consecutive spaces, and
tab-separated text.

## Goal
Fix `src/text_stats.py` so `count_words()` handles empty strings, multiple
consecutive spaces, and non-space whitespace correctly.

## The bug
```python
# BUG: literal ' ' split — empty tokens, ignores tabs
return len(text.split(' '))

# Fix:
return len(text.split())
```

## Failing tests (3/7 fail initially)
```
test_empty_string  ← FAILS (bug returns 1 for '')
test_double_space  ← FAILS (bug returns 3 for 'hello  world')
test_tab_separator ← FAILS (bug returns 1 for 'hello\tworld')
```
