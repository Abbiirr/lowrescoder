# TASK-101: Fix Token Counter Characters vs Words (langflow-ai/langflow pattern)

## Source
Inspired by langflow-ai/langflow token counting. The function counts characters
(`len(text)`) instead of whitespace-split tokens.

## Goal
Fix `src/token_counter.py` so `count_tokens()` returns word count via
`len(text.split())`.

## The bug
```python
# BUG: character count
return len(text)

# Fix: word/token count
return len(text.split())
```

## Failing tests (3/7 fail initially)
```
test_two_word_count     ← FAILS (11 != 2)
test_three_word_count   ← FAILS (13 != 3)
test_sentence_token_count ← FAILS (18 != 4)
```
