# TASK-241: Fix split_into_chunks Drops Last Single-Character Chunk (bat pattern)

## Source
Inspired by sharkdp/bat text paging. Using len(text)-1 as the range stop
drops the last character when text length ≡ 1 (mod size).

## Goal
Fix `src/text_chunker.py` so `split_into_chunks()` uses `len(text)` as the
range stop.

## The bug
```python
# BUG: stop is len(text)-1
return [text[i:i+size] for i in range(0, len(text) - 1, size)]

# Fix:
return [text[i:i+size] for i in range(0, len(text), size)]
```

## Failing tests (3/7 fail initially)
```
test_odd_length          ← FAILS ('abcde' size=2 → bug:['ab','cd'], correct:['ab','cd','e'])
test_longer_odd          ← FAILS ('abcdefg' → bug drops 'g')
test_size_four_remainder_one ← FAILS ('abcde' size=4 → bug:['abcd'], correct:['abcd','e'])
```
