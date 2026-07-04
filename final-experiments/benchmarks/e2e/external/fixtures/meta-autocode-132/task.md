# TASK-132: Fix Git Log Parser Split Count (jesseduffield/lazygit pattern)

## Source
Inspired by lazygit git log parsing. `split('|', 1)` splits into only 2
parts (hash and "author|message"), so author and message are merged.

## Goal
Fix `src/git_log_parser.py` so `parse_commit_line()` splits into exactly
3 parts: hash, author, message.

## The bug
```python
# BUG: maxsplit=1 — only yields [hash, 'author|message']
parts = line.split('|', 1)

# Fix: maxsplit=2
parts = line.split('|', 2)
```

## Failing tests (3/7 fail initially)
```
test_author_is_parsed   ← FAILS (author = 'Alice|Fix bug')
test_message_is_parsed  ← FAILS (message = '')
test_message_with_pipe  ← FAILS (author = 'Bob|Merge: a|b')
```
