# TASK-014: Fix Display Truncation Suffix Overflow (lazygit pattern)

## Source
Inspired by jesseduffield/lazygit terminal column rendering.
Appending suffix after cutting to max_len overflows the column:
result length = max_len + len(suffix) instead of max_len.

## Goal
Fix `src/display.py` so `truncate()` returns at most `max_len` characters.

## The bug
```python
# BUG: max_len chars + suffix → total > max_len
return text[:max_len] + suffix

# Fix: reserve space for suffix first
return text[:max_len - len(suffix)] + suffix
```

## All 7 tests must pass
```
test_short_text_unchanged         ← passes
test_exact_length_unchanged       ← passes
test_truncated_respects_max_len   ← FAILS (len = max_len + 1)
test_truncated_ends_with_suffix   ← passes
test_truncated_multi_char_suffix  ← FAILS (len = max_len + 3 with "...")
test_pad_or_truncate_exact_width  ← FAILS (relies on truncate being correct)
test_pad_or_truncate_short_padded ← passes
```
