# TASK-013: Fix Commit Counter Assignment Bug (gitea pattern)

## Source
Inspired by go-gitea/gitea contributor statistics.
Classic harness-bench v2 pattern: `= 1` instead of `+= 1` resets every
author's count on each commit, so no contributor ever shows more than 1.

## Goal
Fix `src/commit_stats.py`: change `stats[author] = 1` to `stats[author] += 1`.

## The bug
```python
# BUG: resets to 1 every iteration
stats[author] = 1

# Fix: accumulate
stats[author] += 1
```

## All 7 tests must pass
```
test_single_author_three_commits  ← FAILS (returns {"Alice": 1} not 3)
test_two_authors_correct_counts   ← FAILS (all counts = 1)
test_single_commit_is_one         ← passes (1 commit = count 1 either way)
test_empty_returns_empty          ← passes
test_top_contributor_correct      ← FAILS (all tied at 1, wrong winner)
test_top_contributor_single       ← passes
test_top_contributor_empty        ← passes
```
