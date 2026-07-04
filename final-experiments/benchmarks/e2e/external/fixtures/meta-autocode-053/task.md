# TASK-053: Fix Unified Diff Line Counter (jesseduffield/lazygit pattern)

## Source
Inspired by jesseduffield/lazygit diff stats parsing. In a unified diff,
lines starting with `+++` and `---` are file headers, not actual added/removed
lines. The bug counts them as code changes.

## Goal
Fix `src/diff_counter.py` so `count_diff_lines()` skips lines starting with
`+++` or `---` before counting `+`/`-` lines.

## The bug
```python
# BUG: '+++' matches startswith('+') and '---' matches startswith('-')
if line.startswith('+'):
    added += 1
elif line.startswith('-'):
    removed += 1

# Fix: skip headers first
if line.startswith('+++') or line.startswith('---'):
    continue
if line.startswith('+'):
    added += 1
elif line.startswith('-'):
    removed += 1
```

## Failing tests (3/7 fail initially)
```
test_headers_only_excluded        ← FAILS (--- and +++ counted as changes)
test_realistic_diff_with_headers  ← FAILS (header lines inflate counts)
test_multi_file_diff_headers      ← FAILS (multiple file headers double-counted)
```
