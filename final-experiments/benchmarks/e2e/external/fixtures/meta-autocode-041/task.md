# TASK-041: Fix Theme List Case-Sensitive Sort (sharkdp/bat pattern)

## Source
Inspired by sharkdp/bat `--list-themes` output. bat sorts theme names
case-insensitively so users see a natural alphabetical list. The bug uses
`sorted()` without a key, which sorts by ASCII value and places all uppercase
names before all lowercase ones.

## Goal
Fix `src/theme_sorter.py` so `list_themes()` sorts case-insensitively.

## The bug
```python
# BUG: case-sensitive — 'Zenburn' (Z=90) before 'abyss' (a=97)
return sorted(themes)

# Fix: sort by lowercase key
return sorted(themes, key=str.lower)
```

## Failing tests (3/7 fail initially)
```
test_uppercase_interspersed      ← FAILS ('Monokai' before 'abyss' instead of after)
test_capital_before_lowercase_bug ← FAILS ('Zenburn' before 'abyss' instead of after)
test_mixed_case_full_list        ← FAILS ('Dracula','Nord' before 'gruvbox' instead of interleaved)
```
