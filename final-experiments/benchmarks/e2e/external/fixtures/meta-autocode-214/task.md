# TASK-214: Fix format_line_number Missing Right-Justification (bat pattern)

## Source
Inspired by sharkdp/bat line number display. Line numbers must be padded to
a consistent column width so vertical alignment is preserved.

## Goal
Fix `src/line_formatter.py` so `format_line_number()` right-justifies the
number to the given width.

## The bug
```python
# BUG: no padding
return str(n)

# Fix:
return str(n).rjust(width)
```

## Failing tests (3/7 fail initially)
```
test_single_digit_width_four  ← FAILS (1 in width 4: bug:'1', correct:'   1')
test_two_digit_width_five     ← FAILS (42 in width 5: bug:'42', correct:'   42')
test_three_digit_width_six    ← FAILS (100 in width 6: bug:'100', correct:'   100')
```
