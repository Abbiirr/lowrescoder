# TASK-040: Fix Memo Word Count Whitespace Handling (usememos/memos pattern)

## Source
Inspired by usememos/memos memo word count feature. The word count should
split on any whitespace (spaces, tabs, consecutive spaces). The bug uses
`str.split(' ')` which only splits on a single space character, so tabs and
multiple consecutive spaces inflate or incorrectly handle the word count.

## Goal
Fix `src/word_count.py` so `count_words()` correctly handles tabs and multiple
consecutive spaces by using `str.split()` (no argument).

## The bug
```python
# BUG: only splits on single space — tabs and multi-space not handled
return len(content.split(' '))

# Fix: split on any whitespace
return len(content.split())
```

## Failing tests (3/7 fail initially)
```
test_tab_separated_words     ← FAILS ("hello\tworld" → 1 word not 2)
test_double_space_between_words ← FAILS ("a  b" → 3 not 2)
test_mixed_whitespace        ← FAILS ("x\t y  z" → 4 not 3)
```
