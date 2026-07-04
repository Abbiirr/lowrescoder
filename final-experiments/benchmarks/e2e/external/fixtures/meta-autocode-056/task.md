# TASK-056: Fix Plugin Enforce Ordering (vitejs/vite pattern)

## Source
Inspired by vitejs/vite plugin pipeline. Plugins with `enforce: 'pre'` must
run before normal plugins, and `enforce: 'post'` plugins must run last. The
bug returns plugins in registration order, ignoring the enforce property.

## Goal
Fix `src/plugin_sorter.py` so `sort_plugins()` returns plugins ordered:
`pre` → (no enforce) → `post`.

## The bug
```python
# BUG: insertion order, enforce ignored
return plugins

# Fix: sort by enforce priority
ORDER = {'pre': 0, None: 1, 'post': 2}
return sorted(plugins, key=lambda p: ORDER.get(p.get('enforce'), 1))
```

## Failing tests (3/7 fail initially)
```
test_pre_before_normal          ← FAILS ([normal, pre] not reordered to [pre, normal])
test_post_after_normal          ← FAILS ([post, normal] not reordered to [normal, post])
test_full_ordering_pre_normal_post ← FAILS ([post, normal, pre] stays wrong order)
```
