# TASK-192: Fix Param Name Validator Allows Python Keywords (fastapi pattern)

## Source
Inspired by fastapi/fastapi path parameter validation. Using only
`str.isidentifier()` accepts Python reserved keywords like `class`, `return`,
`for` as valid parameter names, which would cause syntax errors.

## Goal
Fix `src/param_checker.py` so `is_valid_param_name()` also rejects reserved
keywords using `keyword.iskeyword()`.

## The bug
```python
# BUG: keywords accepted as valid names
return name.isidentifier()

# Fix:
return name.isidentifier() and not keyword.iskeyword(name)
```

## Failing tests (3/7 fail initially)
```
test_class_keyword  ← FAILS ('class' passes isidentifier — bug True)
test_return_keyword ← FAILS ('return' is a keyword — bug True)
test_for_keyword    ← FAILS ('for' is a keyword — bug True)
```
