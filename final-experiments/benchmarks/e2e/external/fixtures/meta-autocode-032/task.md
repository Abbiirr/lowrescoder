# TASK-032: Fix Issue Label Deduplication (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea issue label management. Adding labels to an issue
should be idempotent — if label 5 is already on the issue, adding it again
should not create a duplicate. The bug concatenates lists without deduplication.

## Goal
Fix `src/label_manager.py` so `add_labels_to_issue()` returns the combined
list with duplicates removed and original order preserved.

## The bug
```python
# BUG: concatenates without deduplication
return existing_labels + new_labels

# Fix: deduplicate preserving order
seen = set()
result = []
for label in existing_labels + new_labels:
    if label not in seen:
        seen.add(label)
        result.append(label)
return result
```

## Failing tests (3/7 fail initially)
```
test_add_existing_label_no_dup  ← FAILS ([1,2]+[1] = [1,2,1])
test_all_new_are_duplicates     ← FAILS ([1,2,3]+[1,2] = [1,2,3,1,2])
test_mixed_new_and_existing     ← FAILS ([1]+[1,2] = [1,1,2])
```
