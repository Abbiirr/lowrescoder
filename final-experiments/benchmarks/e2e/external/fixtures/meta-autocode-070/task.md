# TASK-070: Fix PR Closing Issue Detection Case Sensitivity (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea PR-to-issue auto-close feature. Keywords like
`Closes #42`, `closes #42`, and `CLOSES #42` should all trigger closing
issue #42. The bug uses a case-sensitive regex, missing lowercase/uppercase
variants.

## Goal
Fix `src/pr_issue_finder.py` so `find_closing_issues()` matches the 'Closes'
keyword case-insensitively using `re.IGNORECASE`.

## The bug
```python
# BUG: case-sensitive
re.findall(r'Closes #(\d+)', pr_description)

# Fix: case-insensitive
re.findall(r'Closes #(\d+)', pr_description, re.IGNORECASE)
```

## Failing tests (3/7 fail initially)
```
test_closes_lowercase              ← FAILS ('closes #42' → [], expected [42])
test_closes_all_caps               ← FAILS ('CLOSES #7' → [], expected [7])
test_closes_mid_sentence_lowercase ← FAILS ('closes #15' → [], expected [15])
```
