# TASK-036: Fix CSS Module Class Name Collision (vitejs/vite pattern)

## Source
Inspired by vitejs/vite CSS module scoping. Vite generates unique scoped class
names by hashing the file path and class name together. The bug hashes only the
class name, so `.title` in `Button.module.css` and `.title` in `Header.module.css`
get the same hash — a collision that causes style leakage.

## Goal
Fix `src/css_module.py` so `generate_css_module_class()` includes `file_path`
in the hash to guarantee uniqueness across files.

## The bug
```python
# BUG: file_path not included — same class name in two files collides
hash_val = hashlib.md5(class_name.encode()).hexdigest()[:6]

# Fix: include file_path in hash
hash_val = hashlib.md5(f"{file_path}:{class_name}".encode()).hexdigest()[:6]
```

## Failing tests (3/7 fail initially)
```
test_collision_title_across_files    ← FAILS (both files' 'title' get same hash)
test_collision_name_across_files     ← FAILS (both files' 'name' collide)
test_collision_wrapper_across_files  ← FAILS (both files' 'wrapper' collide)
```
