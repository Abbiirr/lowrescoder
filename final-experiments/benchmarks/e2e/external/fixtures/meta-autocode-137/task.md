# TASK-137: Fix Search Indexer Overwrite Bug (vitejs/vite pattern)

## Source
Inspired by vite plugin search indexing. When multiple documents contain
the same word, the index entry is overwritten instead of accumulated.

## Goal
Fix `src/search_indexer.py` so `build_index()` appends doc_ids to
existing entries rather than overwriting them.

## The bug
```python
# BUG: overwrites — only last doc_id kept per word
index[word] = [doc_id]

# Fix: append
if word not in index:
    index[word] = []
index[word].append(doc_id)
```

## Failing tests (3/7 fail initially)
```
test_word_in_multiple_docs      ← FAILS (only last doc in index)
test_shared_word_all_docs_indexed ← FAILS (len == 1 not 3)
test_partial_shared_word        ← FAILS (doc 10 missing from 'foo')
```
