# TASK-109: Fix Slug Generator Space Separator (usememos/memos pattern)

## Source
Inspired by usememos/memos URL slug generation. URL slugs use hyphens (`-`)
not underscores (`_`) as word separators.

## Goal
Fix `src/slug_generator.py` so `generate_slug()` replaces spaces with `-`
and allows `-` in the character set.

## The bug
```python
# BUG: underscore separator
slug = re.sub(r'\s+', '_', slug)
slug = re.sub(r'[^a-z0-9_]', '', slug)

# Fix:
slug = re.sub(r'\s+', '-', slug)
slug = re.sub(r'[^a-z0-9-]', '', slug)
```

## Failing tests (3/7 fail initially)
```
test_spaces_become_hyphens  ← FAILS ('hello_world' != 'hello-world')
test_multi_word_slug        ← FAILS (underscores instead of hyphens)
test_no_underscores_in_slug ← FAILS (underscore found)
```
