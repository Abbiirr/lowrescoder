# TASK-006: Fix Pydantic v2 Color Encoder (harness-bench pattern)

## Source
Inspired by fastapi/fastapi PR#15101 — a real case from harness-bench v2 where
Codex xhigh (81.5%) and Claude failed. Type: compatibility bug, Pydantic v2 deprecation.

## Goal
Fix `src/color_encoder.py` so `encode_color()` handles both:
- Legacy `pydantic.v1.color.Color` (has `.as_hex()`)
- Modern `pydantic_extra_types.color.Color` (has `.as_named()`, NOT `.as_hex()`)

## The bug
```python
# Current code — crashes on modern Color:
return value.as_hex()  # AttributeError if pydantic_extra_types Color
```

## The fix
Use `hasattr` or try/except to detect which Color type you have:
- If object has `as_hex()` → call it (legacy path)
- Else if object has `as_named()` → call `as_named(fallback=True)` (modern path)
- Else → `str(value)` as final fallback

## All 6 tests must pass:
```
test_encode_none
test_encode_string_passthrough
test_encode_legacy_color
test_encode_modern_color         ← currently fails (AttributeError)
test_encode_modern_color_no_as_hex ← currently fails
test_encode_both_color_types_work   ← currently fails
```
