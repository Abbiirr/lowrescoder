# TASK-067: Fix CR Line Ending Normalization (sharkdp/bat pattern)

## Source
Inspired by sharkdp/bat text processing. bat normalizes line endings to Unix
`\n`. Old Mac files use bare `\r` (carriage return only) as line endings. The
bug only replaces Windows `\r\n` pairs, leaving standalone `\r` unchanged.

## Goal
Fix `src/line_normalizer.py` so `normalize_line_endings()` also replaces
standalone `\r` with `\n`.

## The bug
```python
# BUG: only handles \r\n — standalone \r left in place
return text.replace('\r\n', '\n')

# Fix: handle both
return text.replace('\r\n', '\n').replace('\r', '\n')
```

## Failing tests (3/7 fail initially)
```
test_cr_only           ← FAILS ('a\rb' stays 'a\rb', expected 'a\nb')
test_mixed_crlf_and_cr ← FAILS ('a\r\nb\rc' → 'a\nb\rc', expected 'a\nb\nc')
test_multiple_cr       ← FAILS ('x\ry\rz' stays, expected 'x\ny\nz')
```
