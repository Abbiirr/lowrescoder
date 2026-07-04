# TASK-044: Fix Multi-Line Memo Tag Extraction (usememos/memos pattern)

## Source
Inspired by usememos/memos hashtag extraction. Memos can span multiple lines,
and hashtags on any line should be found. The bug splits on newline and only
processes `split('\n')[0]` — the first line.

## Goal
Fix `src/tag_extractor.py` so `extract_tags_from_memo()` finds #tags on all
lines.

## The bug
```python
# BUG: only first line processed
first_line = content.split('\n')[0]
words = first_line.split()

# Fix: process all lines
words = content.split()
```

## Failing tests (3/7 fail initially)
```
test_tag_on_second_line     ← FAILS ('first\n#python' → [])
test_tags_split_across_lines ← FAILS ('#a\n#b' → ['a'] not ['a','b'])
test_tag_only_on_last_line  ← FAILS (tag on line 3 missed)
```
