# TASK-196: Fix Syntax Highlighter Case-Sensitive Extension Check (bat pattern)

## Source
Inspired by sharkdp/bat file type detection. The extension lookup is
case-sensitive, so files with uppercase extensions like `.PY`, `.JS`, `.CSS`
are not recognised for syntax highlighting.

## Goal
Fix `src/syntax_detector.py` so `should_highlight()` normalises the
extension to lowercase before the lookup.

## The bug
```python
# BUG: no lowercase normalisation
ext = ('.' + filename.rsplit('.', 1)[1]) if '.' in filename else ''

# Fix:
ext = ('.' + filename.rsplit('.', 1)[1]).lower() if '.' in filename else ''
```

## Failing tests (3/7 fail initially)
```
test_uppercase_py  ← FAILS ('script.PY' → .PY not in set → False)
test_uppercase_js  ← FAILS ('app.JS' → .JS not in set → False)
test_uppercase_css ← FAILS ('styles.CSS' → .CSS not in set → False)
```
