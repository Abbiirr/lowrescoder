# TASK-077: Fix Line Number Padding Width (sharkdp/bat pattern)

## Source
Inspired by sharkdp/bat line number display. The padding width should match
the number of digits in `total_lines`, so small files (< 100 lines) use
narrower padding than large files. The bug hard-codes width=4.

## Goal
Fix `src/line_formatter.py` so `format_line_number()` computes the width
from `len(str(total_lines))`.

## The bug
```python
# BUG: always width 4
width = 4

# Fix: compute from total
width = len(str(total_lines))
```

## Failing tests (3/7 fail initially)
```
test_small_file_width_2  ← FAILS (50-line file: '   1' instead of ' 1')
test_single_digit_total  ← FAILS (9-line file: '   3' instead of '3')
test_two_digit_total     ← FAILS (99-line file: '  42' instead of '42')
```
