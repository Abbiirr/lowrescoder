# TASK-084: Fix Tag Extractor Hyphen Support (usememos/memos pattern)

## Source
Inspired by usememos/memos tag parsing. Memo tags like `#open-source` must
be extracted with their full hyphenated name.

## Goal
Fix `src/tag_extractor.py` so `extract_tags()` matches hyphenated tag names.

## The bug
```python
# BUG: no hyphen in character class
matches = re.findall(r'#([a-zA-Z0-9_]+)', content)

# Fix: include hyphen
matches = re.findall(r'#([a-zA-Z0-9_-]+)', content)
```

## Failing tests (3/7 fail initially)
```
test_hyphenated_tag          ← FAILS (['open'] != ['open-source'])
test_hyphenated_tag_in_sentence ← FAILS ('self-hosted' not in ['self'])
test_mixed_tags              ← FAILS (hyphen part truncated)
```
