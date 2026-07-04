# TASK-129: Fix Template Renderer Double-Brace (usememos/memos pattern)

## Source
Inspired by memos template rendering. Uses single curly braces for
substitution but templates use double curly braces `{{key}}`.

## Goal
Fix `src/template_renderer.py` so `render_template()` replaces `{{key}}`
placeholders, not `{key}`.

## The bug
```python
# BUG: single brace — doesn't match {{key}} templates
result = result.replace('{' + key + '}', str(value))

# Fix: double brace
result = result.replace('{{' + key + '}}', str(value))
```

## Failing tests (3/7 fail initially)
```
test_double_brace_template  ← FAILS ('{{name}}' not substituted)
test_double_brace_multiple  ← FAILS (all placeholders remain)
test_double_brace_with_value ← FAILS ('{{count}}' not substituted)
```
