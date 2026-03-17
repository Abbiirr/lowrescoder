# Task: Fix a Broken Git Repository

## Objective

The git repository in `repo/` is in a broken state. It has a detached HEAD and there are uncommitted changes that must not be lost.

## Requirements

1. The `repo/` directory must end up on the `main` branch (not in detached HEAD state).
2. The file `repo/newfile.txt` must exist and contain `important new work`.
3. All changes must be committed (no uncommitted modifications in the working tree).
4. The repository must be in a clean state (`git status` shows nothing to commit).

## Current State

- The repo has 2 commits on `main`.
- HEAD is detached at the latest commit.
- There are uncommitted changes: `newfile.txt` (new) and `file.txt` (modified).

## Safe Recovery Hint

One reliable sequence is:

1. Stash tracked and untracked changes.
2. Switch back to `main`.
3. Restore the stash.
4. Commit the restored changes.

Do not lose `newfile.txt`, and do not leave the repo detached.

## Files

- `repo/` — the git repository to fix
