# TASK-157: Fix Vowel Counter Off-by-One (uptime-kuma pattern)

## Source
Inspired by uptime-kuma text processing utilities. `text[1:]` skips the first
character — words starting with a vowel have that vowel missed.

## Goal
Fix `src/text_analyzer.py` so `count_vowels()` counts all vowels including the
first character.

## The bug
```python
# BUG: starts at index 1, skips first char
return sum(1 for c in text[1:] if c.lower() in 'aeiou')

# Fix:
return sum(1 for c in text if c.lower() in 'aeiou')
```

## Failing tests (3/7 fail initially)
```
test_apple  ← FAILS (1 instead of 2 — misses leading 'a')
test_ocean  ← FAILS (2 instead of 3 — misses leading 'o')
test_air    ← FAILS (1 instead of 2 — misses leading 'a')
```
