# TASK-079: Fix Memo Pin Toggle (usememos/memos pattern)

## Source
Inspired by usememos/memos pin-to-top feature. Calling `toggle_pin` on an
already-pinned memo should unpin it. The bug always sets `pinned=True`,
making it impossible to unpin.

## Goal
Fix `src/pin_toggler.py` so `toggle_pin()` sets `pinned = not memo.get('pinned', False)`.

## The bug
```python
# BUG: always True — can't unpin
memo['pinned'] = True

# Fix: toggle
memo['pinned'] = not memo.get('pinned', False)
```

## Failing tests (3/7 fail initially)
```
test_pinned_memo_gets_unpinned       ← FAILS (True stays True, should be False)
test_double_toggle_returns_to_original ← FAILS (False→True→True, should be False)
test_pinned_memo_unpin_preserves_content ← FAILS (pinned stays True, should be False)
```
