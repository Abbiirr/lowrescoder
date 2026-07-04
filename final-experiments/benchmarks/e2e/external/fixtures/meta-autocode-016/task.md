# TASK-016: Fix Tag Parser Trailing Punctuation (usememos/memos pattern)

## Source
Inspired by usememos/memos inline hashtag parsing.
Tags like "#bug." end a sentence — the period is punctuation, not part of the tag.

## Goal
Fix `src/tag_parser.py` so `extract_tags()` strips trailing punctuation
(`.,!?;:`) from extracted tag names.

## The bug
```python
# BUG: includes trailing punctuation
tags.append(word[1:])

# Fix: strip trailing punctuation
tags.append(word[1:].rstrip(".,!?;:"))
```

## Failing tests (3/7 fail initially)
```
test_tag_trailing_period      ← FAILS ("bug." not "bug")
test_tag_trailing_comma       ← FAILS ("python," not "python")
test_tag_trailing_exclamation ← FAILS ("feature!" not "feature")
```
