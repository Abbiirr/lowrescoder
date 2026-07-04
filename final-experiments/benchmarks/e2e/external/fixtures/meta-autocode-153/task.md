# TASK-153: Fix Title Case Apostrophe Handling (bat pattern)

## Source
Inspired by sharkdp/bat syntax display. `str.title()` treats apostrophes as
word boundaries, uppercasing the character after them — "Don'T" instead of
"Don't".

## Goal
Fix `src/text_formatter.py` so `to_title_case()` correctly handles
contractions.

## The bug
```python
# BUG: str.title() uppercases after apostrophes
return text.title()

# Fix: capitalize each whitespace-delimited word manually
return ' '.join(w.capitalize() for w in text.split())
```

## Failing tests (3/7 fail initially)
```
test_contraction_dont  ← FAILS ("Don'T Stop" instead of "Don't Stop")
test_contraction_its   ← FAILS ("It'S Alive" instead of "It's Alive")
test_contraction_weve  ← FAILS ("We'Ve Got This" instead of "We've Got This")
```
