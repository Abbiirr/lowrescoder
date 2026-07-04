# Task: Recover a Deleted Git Branch

## Objective

A branch `feature/important-work` was accidentally deleted from the repository in `repo/`. Recover it.

## Requirements

1. Branch `feature/important-work` must exist again.
2. The branch must contain a file `feature.py` with the function `do_important_work()`.
3. The branch must have at least 2 commits (the original commits).
4. The `main` branch must remain unchanged.

## Current State

- The repo has a `main` branch with 2 commits.
- `feature/important-work` was created, had 2 commits, then was deleted with `git branch -D`.
- The commits still exist in the reflog.

## Hint

Use `git reflog` to find the deleted branch's last commit, then recreate the branch.

## Files

- `repo/` — the git repository
