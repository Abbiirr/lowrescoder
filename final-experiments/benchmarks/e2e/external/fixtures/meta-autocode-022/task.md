# TASK-022: Fix Wiki Name Sanitizer Consecutive Spaces (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea wiki page filename sanitization.
Wiki page titles are converted to filenames by replacing spaces with
underscores. The bug: `.replace(" ", "_")` replaces each space individually,
so consecutive spaces produce double underscores and leading spaces produce
leading underscores.

## Goal
Fix `src/wiki_name.py` so `sanitize_wiki_name()` collapses consecutive
whitespace to a single underscore and strips leading/trailing whitespace.

## The bug
```python
# BUG: each space becomes its own underscore — consecutive spaces double up
return name.replace(" ", "_")

# Fix: strip and collapse with regex
import re
return re.sub(r'\s+', '_', name.strip())
```

## Failing tests (3/7 fail initially)
```
test_double_space_collapses  ← FAILS ("my__page" not "my_page")
test_leading_space_stripped  ← FAILS ("__leading" not "leading")
test_triple_space_collapses  ← FAILS ("a___b" not "a_b")
```
