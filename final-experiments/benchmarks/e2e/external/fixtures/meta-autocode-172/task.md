# TASK-172: Fix camelCase to snake_case Leading Underscore (lazygit pattern)

## Source
Inspired by jesseduffield/lazygit variable naming utilities. Inserting `_`
before every uppercase letter adds a spurious leading underscore for
PascalCase names ('MyClass' → '_my_class').

## Goal
Fix `src/case_converter.py` so `camel_to_snake()` strips any leading
underscore from the result.

## The bug
```python
# BUG: no lstrip — PascalCase gets leading '_'
return re.sub(r'([A-Z])', r'_\1', name).lower()

# Fix:
return re.sub(r'([A-Z])', r'_\1', name).lower().lstrip('_')
```

## Failing tests (3/7 fail initially)
```
test_pascal_simple   ← FAILS ('_my_class' instead of 'my_class')
test_pascal_multi    ← FAILS ('_pascal_case' instead of 'pascal_case')
test_pascal_acronym  ← FAILS ('_http_request' instead of 'http_request')
```
