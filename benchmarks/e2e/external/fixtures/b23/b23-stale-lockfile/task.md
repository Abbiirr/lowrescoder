# Task: Fix Out-of-Sync Lock File

## Objective

The `package-lock.json` is out of sync with `package.json`. Reconcile the lock file so it accurately reflects all dependencies declared in `package.json`.

## Requirements

1. `package-lock.json` must exist after the fix.
2. Every dependency in `package.json` (both `dependencies` and `devDependencies`) must have a corresponding entry in `package-lock.json`.
3. No extra dependencies should be in `package-lock.json` that are not in `package.json`.
4. The `package-lock.json` must be valid JSON.
5. The version ranges in `package-lock.json` entries must be compatible with the version constraints in `package.json`.

## Current State

- `package.json` — Lists 4 dependencies and 2 devDependencies.
- `package-lock.json` — Stale: missing 2 dependencies that were recently added to `package.json`, and contains 1 dependency that was removed from `package.json`.

## Note

This is a **simulated** Node.js project. You do NOT need `npm` or `node` installed. Fix the lock file by editing it directly to match `package.json`. Use realistic version numbers.

## Files

- `package.json` — Source of truth for dependencies
- `package-lock.json` — Stale lock file to fix
