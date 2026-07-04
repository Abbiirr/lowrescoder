# TASK-049: Fix Tab Width Expansion (sharkdp/bat pattern)

## Source
Inspired by sharkdp/bat's `--tabs` flag which expands tab characters to a
configurable number of spaces. The bug hard-codes 4 spaces regardless of the
`tab_width` argument.

## Goal
Fix `src/tab_expander.py` so `expand_tabs(line, tab_width)` replaces each
`\t` with exactly `tab_width` spaces.

## The bug
```python
# BUG: ignores tab_width, always uses 4 spaces
return line.replace('\t', '    ')

# Fix: use the parameter
return line.replace('\t', ' ' * tab_width)
```

## Failing tests (3/7 fail initially)
```
test_tab_width_2 ← FAILS ('hello\tworld' with width=2 returns 4 spaces, not 2)
test_tab_width_8 ← FAILS ('hello\tworld' with width=8 returns 4 spaces, not 8)
test_tab_width_1 ← FAILS ('a\tb' with width=1 returns 4 spaces, not 1)
```
