# TASK-250: Fix count_lines() count('\n') Undercounts Lines Without Trailing Newline (bat pattern)

## Source
Inspired by sharkdp/bat line counting logic. Counting '\n' characters misses the last line
when text doesn't end with a newline.

## Goal
Fix `src/line_counter.py` so `count_lines()` correctly counts all lines.

## The bug
```python
# BUG: undercounts by 1 for text not ending with newline
return text.count('\n')

# Fix:
return len(text.splitlines()) if text else 0
```

## Failing tests (3/7 fail initially)
```
test_single_word_no_newline ← FAILS ('hello' → bug:0, correct:1)
test_two_lines_no_trailing  ← FAILS ('a\nb' → bug:1, correct:2)
test_three_lines_no_trailing ← FAILS ('a\nb\nc' → bug:2, correct:3)
```
