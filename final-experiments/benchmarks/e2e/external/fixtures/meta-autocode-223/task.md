# TASK-223: Fix replace_tabs Uses 1 Space Instead of width Spaces (bat pattern)

## Source
Inspired by sharkdp/bat tab expansion. The function replaces tabs with a
hard-coded single space instead of using the configurable `width` parameter.

## Goal
Fix `src/tab_replacer.py` so `replace_tabs()` replaces each tab with
`width` spaces (default 4).

## The bug
```python
# BUG: hard-coded single space
return text.replace('\t', ' ')

# Fix:
return text.replace('\t', ' ' * width)
```

## Failing tests (3/7 fail initially)
```
test_tab_at_start       ← FAILS ('\thello' → bug:' hello', correct:'    hello')
test_tab_between_words  ← FAILS ('a\tb' → bug:'a b', correct:'a    b')
test_two_tabs           ← FAILS ('\t\t' → bug:'  ', correct:'        ')
```
