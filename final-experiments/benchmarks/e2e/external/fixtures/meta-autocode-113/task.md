# TASK-113: Fix Markdown Stripper Missing Backtick Removal (usememos/memos pattern)

## Source
Inspired by usememos/memos plain-text export. The markdown stripper handles
bold and italic but misses inline code backticks.

## Goal
Fix `src/markdown_stripper.py` so `strip_markdown()` also removes backtick
code spans.

## The bug
```python
# BUG: no backtick removal
# Missing: text = re.sub(r'`(.+?)`', r'\1', text)

# Fix: add after existing substitutions
text = re.sub(r'`(.+?)`', r'\1', text)
```

## Failing tests (3/7 fail initially)
```
test_strips_inline_code  ← FAILS (backticks remain)
test_strips_code_only    ← FAILS ('`code`' != 'code')
test_strips_mixed        ← FAILS (backtick in result)
```
