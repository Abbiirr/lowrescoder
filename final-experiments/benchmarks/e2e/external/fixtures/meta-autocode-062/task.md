# TASK-062: Fix Case-Insensitive Search Highlight (usememos/memos pattern)

## Source
Inspired by usememos/memos search result highlighting. The highlight function
should wrap all case-insensitive matches with `<mark>` tags. The bug uses
`str.replace()` which is case-sensitive.

## Goal
Fix `src/search_highlighter.py` so `highlight_matches()` highlights query
matches regardless of case, preserving the original text's casing inside the
`<mark>` tags.

## The bug
```python
# BUG: case-sensitive
return text.replace(query, f'<mark>{query}</mark>')

# Fix: case-insensitive using re.sub
import re
return re.sub(re.escape(query), lambda m: f'<mark>{m.group()}</mark>', text, flags=re.IGNORECASE)
```

## Failing tests (3/7 fail initially)
```
test_uppercase_query_lowercase_text ← FAILS ('HELLO' query misses 'hello' in text)
test_mixed_case_query               ← FAILS ('Bat' query misses 'bat' in text)
test_all_caps_text                  ← FAILS ('search' query misses 'SEARCH' in text)
```
