# TASK-242: Fix summarize_memo Off-By-One in Word Slice (memos pattern)

## Source
Inspired by usememos/memos content preview. Using max_words-1 in the slice
returns one fewer word than the configured limit.

## Goal
Fix `src/memo_summarizer.py` so `summarize_memo()` returns up to `max_words`
words.

## The bug
```python
# BUG: off-by-one
return ' '.join(words[:max_words - 1])

# Fix:
return ' '.join(words[:max_words])
```

## Failing tests (3/7 fail initially)
```
test_exactly_five_words ← FAILS ('a b c d e' → bug:'a b c d', correct:'a b c d e')
test_six_words          ← FAILS (6 words → bug returns 4, correct returns 5)
test_seven_words        ← FAILS (7 words → bug returns 4, correct returns 5)
```
