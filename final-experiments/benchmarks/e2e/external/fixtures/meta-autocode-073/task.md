# TASK-073: Fix Label Color Hex Format Validation (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea label creation. Label colors must be 6-digit hex
codes with a `#` prefix (e.g. `#ff0000`). The bug accepts any non-empty
string, allowing invalid values like `'red'` or `'ff0000'`.

## Goal
Fix `src/color_validator.py` so `is_valid_label_color()` validates against
the regex `^#[0-9a-fA-F]{6}$`.

## The bug
```python
# BUG: any non-empty string accepted
return bool(color)

# Fix: validate hex format
return bool(re.match(r'^#[0-9a-fA-F]{6}$', color))
```

## Failing tests (3/7 fail initially)
```
test_no_hash_prefix_rejected  ← FAILS ('ff0000' accepted, should be rejected)
test_invalid_hex_chars_rejected ← FAILS ('#gggggg' accepted, should be rejected)
test_short_hex_rejected        ← FAILS ('#fff' accepted, should be rejected)
```
