# TASK-145: Fix List Right Rotation (axios/axios pattern)

## Source
Inspired by axios interceptor queue rotation. Rotates left (first element
to back) instead of right (last element to front).

## Goal
Fix `src/list_rotator.py` so `rotate_right()` moves the last element
to the front of the list.

## The bug
```python
# BUG: left rotation
return items[1:] + items[:1]

# Fix: right rotation
return items[-1:] + items[:-1]
```

## Failing tests (3/7 fail initially)
```
test_three_elements  ← FAILS ([2,3,1] instead of [3,1,2])
test_four_elements   ← FAILS ([2,3,4,1] instead of [4,1,2,3])
test_last_becomes_first ← FAILS (result[0] == 'y' not 'z')
```
