# TASK-169: Fix URL Slug Generator Underscore vs Hyphen (fastapi pattern)

## Source
Inspired by fastapi/fastapi URL path generation. URL slugs should use hyphens
(`-`) not underscores (`_`) as word separators per web conventions.

## Goal
Fix `src/slug_generator.py` so `slugify()` replaces spaces with hyphens.

## The bug
```python
# BUG: uses underscore
return text.lower().replace(' ', '_')

# Fix:
return text.lower().replace(' ', '-')
```

## Failing tests (3/7 fail initially)
```
test_two_words            ← FAILS ('hello_world' instead of 'hello-world')
test_three_words          ← FAILS ('foo_bar_baz' instead of 'foo-bar-baz')
test_mixed_case_with_spaces ← FAILS ('hello_world' instead of 'hello-world')
```
