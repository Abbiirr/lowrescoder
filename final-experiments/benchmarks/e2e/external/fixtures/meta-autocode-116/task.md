# TASK-116: Fix Batch Processor Off-By-One Slice (langflow-ai/langflow pattern)

## Source
Inspired by langflow-ai/langflow batch processing. The slice `items[i:i+size-1]`
drops the last item of each batch.

## Goal
Fix `src/batch_processor.py` so `process_in_batches()` uses `items[i:i+batch_size]`.

## The bug
```python
# BUG: -1 drops last item
batch = items[i:i + batch_size - 1]

# Fix:
batch = items[i:i + batch_size]
```

## Failing tests (3/7 fail initially)
```
test_full_batch_all_items    ← FAILS ([1,2] != [1,2,3])
test_multiple_batches_complete ← FAILS (4 != 6)
test_no_item_dropped         ← FAILS (4 not in result)
```
