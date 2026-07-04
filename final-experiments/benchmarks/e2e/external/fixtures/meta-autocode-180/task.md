# TASK-180: Fix JS File Checker Missing .mjs/.cjs Extensions (vite pattern)

## Source
Inspired by vitejs/vite module resolution. Checking only `.js` misses the
ESM (`.mjs`) and CommonJS (`.cjs`) module variants that Vite supports.

## Goal
Fix `src/module_checker.py` so `is_js_file()` recognises `.js`, `.mjs`, and
`.cjs` extensions.

## The bug
```python
# BUG: only .js — misses .mjs and .cjs
return filename.endswith('.js')

# Fix:
return filename.endswith(('.js', '.mjs', '.cjs'))
```

## Failing tests (3/7 fail initially)
```
test_mjs_extension ← FAILS ('module.mjs' → bug returns False)
test_cjs_extension ← FAILS ('common.cjs' → bug returns False)
test_vendor_mjs    ← FAILS ('vendor.mjs'  → bug returns False)
```
