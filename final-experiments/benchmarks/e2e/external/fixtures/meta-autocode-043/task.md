# TASK-043: Fix Commit Date Zero-Padding (jesseduffield/lazygit pattern)

## Source
Inspired by jesseduffield/lazygit commit log date display. Dates must use
ISO-8601 format with zero-padded month and day (YYYY-MM-DD). The bug uses
f-string interpolation without format specifiers, so month 3 becomes '3'
instead of '03'.

## Goal
Fix `src/date_formatter.py` so `format_commit_date()` zero-pads month and day.

## The bug
```python
# BUG: no zero-padding
return f"{year}-{month}-{day}"

# Fix: use :02d format spec
return f"{year}-{month:02d}-{day:02d}"
```

## Failing tests (3/7 fail initially)
```
test_single_digit_month              ← FAILS (2026-3-5 not 2026-03-05)
test_single_digit_month_double_digit_day ← FAILS (2026-3-15 not 2026-03-15)
test_double_digit_month_single_digit_day ← FAILS (2026-12-5 not 2026-12-05)
```
