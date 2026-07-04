# TASK-086: Fix Request Header Merger Content-Type Override (axios/axios pattern)

## Source
Inspired by axios/axios header merging. The merge should not force
`Content-Type: application/json` when the caller has already set one.

## Goal
Fix `src/request_merger.py` so `merge_request_headers()` only sets
Content-Type as a default (when not already present).

## The bug
```python
# BUG: always overwrites Content-Type
result['Content-Type'] = 'application/json'

# Fix: only set if absent
result.setdefault('Content-Type', 'application/json')
```

## Failing tests (3/7 fail initially)
```
test_caller_content_type_preserved  ← FAILS ('application/json' != 'text/plain')
test_request_content_type_preserved ← FAILS ('application/json' != 'multipart/form-data')
test_xml_content_type_not_overwritten ← FAILS ('application/json' != 'application/xml')
```
