# TASK-031: Fix Request Header Merger (axios/axios pattern)

## Source
Inspired by axios/axios default header merging. When making a request, axios
merges instance defaults with per-request config headers so both apply.
The bug returns `config_headers` directly, discarding defaults entirely.

## Goal
Fix `src/header_merger.py` so `merge_request_headers()` returns a dict with
defaults and config headers merged (config wins on key conflicts).

## The bug
```python
# BUG: discards defaults — returns only config_headers
return config_headers

# Fix: merge, config wins
return {**defaults, **config_headers}
```

## Failing tests (3/7 fail initially)
```
test_empty_config_keeps_defaults      ← FAILS ({} config drops all defaults)
test_default_not_in_config_preserved  ← FAILS (Authorization default lost)
test_both_unique_headers_merged       ← FAILS ({'A':'1'} lost when config has {'B':'2'})
```
