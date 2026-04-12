# Task: Resolve a Git Merge Conflict

## Objective

The repository in `repo/` has an unfinished merge with conflicts. Resolve the conflicts and complete the merge.

## Requirements

1. The merge must be completed (no `MERGE_HEAD` present).
2. The file `repo/config.py` must contain BOTH the `DATABASE_URL` from `main` AND the `CACHE_TTL` from the feature branch — no conflict markers.
3. The file `repo/app.py` must import from both `database` and `cache` modules.
4. The repository must be in a clean state (`git status` shows nothing to commit).
5. The merge commit must exist in the history.

## Current State

- Branch `main` modified `config.py` to add `DATABASE_URL` and `app.py` to import `database`.
- Branch `feature/cache` modified `config.py` to add `CACHE_TTL` and `app.py` to import `cache`.
- A merge was started but left with conflicts in both files.
- Conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) are present in the files.

## Files

- `repo/` — the git repository with unresolved merge conflicts
